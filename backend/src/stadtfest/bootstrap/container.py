"""Composition root: creates infrastructure resources and wires ports to adapters."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from arq.connections import ArqRedis
from pydantic import SecretStr
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from stadtfest.adapters.outbound.auth.idp_admin import (
    FakeIdpAdmin,
    KeycloakIdpAdmin,
    ZitadelIdpAdmin,
)
from stadtfest.adapters.outbound.auth.jwks import JwksTokenVerifier
from stadtfest.adapters.outbound.cache.deleted_accounts import RedisDeletedAccounts
from stadtfest.adapters.outbound.cache.redis_cache import RedisCache
from stadtfest.adapters.outbound.cache.redis_client import RedisProbe, create_redis
from stadtfest.adapters.outbound.clock.berlin_clock import BerlinClock
from stadtfest.adapters.outbound.geocoding.fake import FakeGeocoding
from stadtfest.adapters.outbound.geocoding.nominatim import (
    NominatimGeocoding,
    create_nominatim_client,
)
from stadtfest.adapters.outbound.imaging.pillow import PillowImageProcessor
from stadtfest.adapters.outbound.llm.fake import FakeEventFinder
from stadtfest.adapters.outbound.llm.pydantic_ai import (
    LlmConfig,
    LlmKind,
    PydanticAiEventFinder,
    build_model,
)
from stadtfest.adapters.outbound.persistence.accounts import SqlUserRepository
from stadtfest.adapters.outbound.persistence.ai_search import SqlAiSearchRepository, SqlDraftStore
from stadtfest.adapters.outbound.persistence.catalog import SqlCatalog
from stadtfest.adapters.outbound.persistence.categories import SqlCategoryRepository
from stadtfest.adapters.outbound.persistence.database import DatabaseProbe, create_engine
from stadtfest.adapters.outbound.persistence.favorites import SqlFavoriteRepository
from stadtfest.adapters.outbound.persistence.images import SqlImageRepository
from stadtfest.adapters.outbound.persistence.moderation import (
    SqlActiveCategories,
    SqlManagedEventRepository,
)
from stadtfest.adapters.outbound.persistence.notifications import (
    SqlAiSearchOwners,
    SqlDeviceStore,
    SqlNotificationStore,
    SqlRecipients,
    SqlSettingsStore,
)
from stadtfest.adapters.outbound.persistence.outbox import SqlEventFavorites, SqlOutboxStore
from stadtfest.adapters.outbound.push.direct import ApnsConfig, DirectPushSender, FcmConfig
from stadtfest.adapters.outbound.push.disabled import DisabledPushSender
from stadtfest.adapters.outbound.push.expo import ExpoPushSender
from stadtfest.adapters.outbound.queue.arq_jobs import (
    ArqAccountJobs,
    ArqEventQueue,
    ArqPushJobs,
    create_arq_redis,
)
from stadtfest.adapters.outbound.search.brave import BraveWebSearch
from stadtfest.adapters.outbound.search.fake import FakeWebSearch
from stadtfest.adapters.outbound.search.searxng import SearxngWebSearch
from stadtfest.adapters.outbound.sources.http import (
    AllowAllSourceChecker,
    HttpSourceChecker,
    create_source_client,
)
from stadtfest.adapters.outbound.sources.pages import HttpPageReader
from stadtfest.adapters.outbound.storage.s3 import S3Config, S3ObjectStorage
from stadtfest.adapters.outbound.storage.urls import ImageUrls
from stadtfest.application.ai_ingestion.ports import (
    EventFinder,
    PageReader,
    SourceChecker,
    WebSearchPort,
)
from stadtfest.application.ai_ingestion.use_cases import (
    AiSearchSettings,
    CompactAiSearchLogs,
    FailStuckSearches,
    GetAiSearch,
    ListAiSearches,
    RunAiSearch,
    StartAiSearch,
)
from stadtfest.application.collections.use_cases import (
    AddFavorite,
    IsFavorite,
    ListFavorites,
    RemoveFavorite,
)
from stadtfest.application.events.use_cases import (
    CountEvents,
    GetPublicEvent,
    ListActiveCategories,
    SearchEvents,
)
from stadtfest.application.geocoding.ports import GeocodingPort
from stadtfest.application.geocoding.use_cases import (
    Geocode,
    ReverseGeocode,
    ReverseGeocodeEventLocation,
)
from stadtfest.application.health.check_readiness import CheckReadiness
from stadtfest.application.identity.claims import ClaimMapping
from stadtfest.application.identity.ports import IdpAdminPort
from stadtfest.application.identity.use_cases import (
    Authenticate,
    DeleteAccount,
    DeleteIdpUser,
    EnsureAccount,
    GetMe,
    UpdateMe,
)
from stadtfest.application.moderation.categories import (
    CreateCategory,
    DeleteCategory,
    ListModCategories,
    OrderCategories,
    UpdateCategory,
)
from stadtfest.application.moderation.images import (
    AttachImage,
    CreateUpload,
    DeleteImageFiles,
    OrderImages,
    ProcessImage,
    PurgeImages,
    RemoveImage,
    RetryImage,
)
from stadtfest.application.moderation.use_cases import (
    CancelModEvent,
    CreateModEvent,
    DeleteModEvent,
    GetModEvent,
    ListModEvents,
    PublishModEvent,
    UnpublishModEvent,
    UpdateModEvent,
)
from stadtfest.application.notifications.ports import PushProvider, PushSender
from stadtfest.application.notifications.use_cases import (
    CheckPushReceipts,
    DeleteNotification,
    GetNotificationSettings,
    ListNotifications,
    MarkAllNotificationsRead,
    MarkNotificationRead,
    Notify,
    NotifyForDomainEvent,
    PurgeNotifications,
    PushNotifications,
    PushToModerator,
    RegisterDevice,
    RemoveDevice,
    SendReminders,
    UpdateNotificationSettings,
)
from stadtfest.application.outbox.use_cases import HandleDomainEvent, PurgeOutbox, RelayOutbox
from stadtfest.bootstrap.settings import (
    GeocodingProvider,
    IdpAdminProvider,
    LlmProvider,
    Settings,
    WebSearchProvider,
    ai_search_prompt,
)


def _secret(value: SecretStr | None) -> str:
    """Unwrap a secret whose presence the settings validator has checked."""
    return value.get_secret_value() if value else ""


def _idp_admin(settings: Settings, http: httpx.AsyncClient) -> IdpAdminPort:
    issuer = str(settings.auth_issuer)
    match settings.idp_admin_provider:
        case IdpAdminProvider.KEYCLOAK:
            return KeycloakIdpAdmin(
                http,
                issuer,
                settings.idp_admin_client_id or "",
                _secret(settings.idp_admin_client_secret),
            )
        case IdpAdminProvider.ZITADEL:
            return ZitadelIdpAdmin(http, issuer, _secret(settings.idp_admin_token))
        case IdpAdminProvider.FAKE:
            return FakeIdpAdmin()


@dataclass(frozen=True)
class AiSearchParts:
    """The configured building blocks of the AI search (worker and `ai_eval`)."""

    finder: EventFinder
    search: WebSearchPort
    sources: SourceChecker
    pages: PageReader | None
    geocoding: GeocodingPort
    catalog: SqlCatalog
    clock: BerlinClock
    settings: AiSearchSettings


@dataclass
class Container:
    """Process-wide dependencies shared by the API, the worker and the MCP server."""

    settings: Settings
    engine: AsyncEngine
    sessions: async_sessionmaker[AsyncSession]
    redis: Redis
    arq_redis: ArqRedis
    http: httpx.AsyncClient | None
    auth_http: httpx.AsyncClient
    check_readiness: CheckReadiness
    search_events: SearchEvents
    count_events: CountEvents
    get_public_event: GetPublicEvent
    list_active_categories: ListActiveCategories
    geocode: Geocode
    reverse_geocode: ReverseGeocode
    reverse_geocode_event_location: ReverseGeocodeEventLocation
    authenticate: Authenticate
    get_me: GetMe
    update_me: UpdateMe
    delete_account: DeleteAccount
    add_favorite: AddFavorite
    remove_favorite: RemoveFavorite
    list_favorites: ListFavorites
    is_favorite: IsFavorite
    list_mod_events: ListModEvents
    get_mod_event: GetModEvent
    create_mod_event: CreateModEvent
    update_mod_event: UpdateModEvent
    publish_mod_event: PublishModEvent
    unpublish_mod_event: UnpublishModEvent
    cancel_mod_event: CancelModEvent
    delete_mod_event: DeleteModEvent
    relay_outbox: RelayOutbox
    handle_domain_event: HandleDomainEvent
    purge_outbox: PurgeOutbox
    delete_idp_user: DeleteIdpUser
    storage: S3ObjectStorage
    image_urls: ImageUrls
    create_upload: CreateUpload
    attach_image: AttachImage
    order_images: OrderImages
    remove_image: RemoveImage
    retry_image: RetryImage
    process_image: ProcessImage
    purge_images: PurgeImages
    list_mod_categories: ListModCategories
    create_category: CreateCategory
    update_category: UpdateCategory
    order_categories: OrderCategories
    delete_category: DeleteCategory
    ai_http: list[httpx.AsyncClient]
    start_ai_search: StartAiSearch
    get_ai_search: GetAiSearch
    list_ai_searches: ListAiSearches
    run_ai_search: RunAiSearch
    fail_stuck_searches: FailStuckSearches
    compact_ai_search_logs: CompactAiSearchLogs
    ai_parts: AiSearchParts
    push_http: list[httpx.AsyncClient]
    push_provider: PushProvider
    list_notifications: ListNotifications
    mark_notification_read: MarkNotificationRead
    mark_all_notifications_read: MarkAllNotificationsRead
    delete_notification: DeleteNotification
    get_notification_settings: GetNotificationSettings
    update_notification_settings: UpdateNotificationSettings
    register_device: RegisterDevice
    remove_device: RemoveDevice
    push_notifications: PushNotifications
    check_push_receipts: CheckPushReceipts
    send_reminders: SendReminders
    purge_notifications: PurgeNotifications

    @classmethod
    def build(cls, settings: Settings) -> Container:
        """Create all resources and use cases for the given settings.

        Args:
            settings: Validated application settings.

        Returns:
            The wired container. Call `aclose()` on shutdown.
        """
        engine = create_engine(str(settings.database_url))
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        redis = create_redis(str(settings.redis_url))
        cache = RedisCache(redis)
        clock = BerlinClock()
        image_urls = ImageUrls(str(settings.s3_public_base_url))
        storage = S3ObjectStorage(
            S3Config(
                endpoint_url=str(settings.s3_endpoint_url),
                presign_endpoint_url=(
                    str(settings.s3_presign_endpoint_url)
                    if settings.s3_presign_endpoint_url
                    else None
                ),
                bucket=settings.s3_bucket,
                region=settings.s3_region,
                access_key_id=settings.s3_access_key_id,
                secret_access_key=settings.s3_secret_access_key.get_secret_value(),
                timeout_seconds=settings.s3_timeout_seconds,
            )
        )
        catalog = SqlCatalog(sessions, image_urls)

        http: httpx.AsyncClient | None = None
        geocoding: GeocodingPort
        if settings.geocoding_provider is GeocodingProvider.NOMINATIM:
            http = create_nominatim_client(
                str(settings.nominatim_url), settings.geocoding_timeout_seconds
            )
            geocoding = NominatimGeocoding(http)
        else:
            geocoding = FakeGeocoding()

        auth_http = httpx.AsyncClient(timeout=settings.auth_timeout_seconds)
        verifier = JwksTokenVerifier(
            auth_http,
            issuer=str(settings.auth_issuer).rstrip("/"),
            audience=settings.auth_audience,
            jwks_url=str(settings.auth_jwks_url) if settings.auth_jwks_url else None,
            leeway_seconds=settings.auth_leeway_seconds,
        )
        claim_mapping = ClaimMapping(settings.auth_roles_claim)
        users = SqlUserRepository(sessions)
        idp_admin = _idp_admin(settings, auth_http)
        arq_redis = create_arq_redis(str(settings.redis_url))
        deleted_accounts = RedisDeletedAccounts(redis)
        favorites = SqlFavoriteRepository(sessions, image_urls)
        images = SqlImageRepository(sessions)
        categories = SqlCategoryRepository(sessions)
        managed = SqlManagedEventRepository(sessions)
        ensure_account = EnsureAccount(users)
        mod = (managed, clock)
        outbox = SqlOutboxStore(sessions)
        process_image = ProcessImage(images, storage, PillowImageProcessor(), cache)
        ai_http: list[httpx.AsyncClient] = []
        finder, search, sources, pages = _ai_adapters(settings, ai_http)
        ai_settings = AiSearchSettings(
            radius_km=settings.ai_search_radius_km,
            daily_limit=settings.ai_search_daily_limit,
            max_tool_calls=settings.ai_search_max_tool_calls,
            timeout_seconds=settings.ai_search_timeout_s,
            max_page_reads=settings.ai_search_max_page_reads,
            prompt=ai_search_prompt(settings),
        )
        ai_jobs = SqlAiSearchRepository(sessions)
        ai_parts = AiSearchParts(
            finder, search, sources, pages, geocoding, catalog, clock, ai_settings
        )
        run_ai_search = RunAiSearch(
            ai_jobs,
            finder,
            search,
            sources,
            pages,
            geocoding,
            catalog,
            SqlDraftStore(sessions),
            clock,
            ai_settings,
        )
        delete_image_files = DeleteImageFiles(storage)
        push_http: list[httpx.AsyncClient] = []
        sender = _push_sender(settings, push_http)
        notifications = SqlNotificationStore(sessions)
        notification_settings = SqlSettingsStore(sessions)
        devices = SqlDeviceStore(sessions)
        recipients = SqlRecipients(sessions)
        push_jobs = ArqPushJobs(arq_redis)
        notify = Notify(notifications, push_jobs)
        notify_for_domain_event = NotifyForDomainEvent(
            recipients,
            notify,
            PushToModerator(SqlAiSearchOwners(sessions), devices, sender, push_jobs),
        )

        return cls(
            settings=settings,
            engine=engine,
            sessions=sessions,
            redis=redis,
            arq_redis=arq_redis,
            http=http,
            auth_http=auth_http,
            check_readiness=CheckReadiness([DatabaseProbe(engine), RedisProbe(redis)]),
            search_events=SearchEvents(catalog, cache, clock),
            count_events=CountEvents(catalog, cache, clock),
            get_public_event=GetPublicEvent(catalog),
            list_active_categories=ListActiveCategories(catalog, cache),
            geocode=Geocode(geocoding, cache),
            reverse_geocode=ReverseGeocode(geocoding, cache),
            reverse_geocode_event_location=ReverseGeocodeEventLocation(geocoding, cache),
            authenticate=Authenticate(verifier, claim_mapping, deleted_accounts),
            get_me=GetMe(users),
            update_me=UpdateMe(users),
            delete_account=DeleteAccount(
                users,
                idp_admin,
                ArqAccountJobs(arq_redis),
                deleted_accounts,
                token_leeway_seconds=settings.auth_leeway_seconds,
            ),
            delete_idp_user=DeleteIdpUser(idp_admin),
            add_favorite=AddFavorite(favorites, ensure_account),
            remove_favorite=RemoveFavorite(favorites),
            list_favorites=ListFavorites(favorites, clock),
            is_favorite=IsFavorite(favorites),
            list_mod_events=ListModEvents(*mod),
            get_mod_event=GetModEvent(*mod),
            create_mod_event=CreateModEvent(*mod, ensure_account),
            update_mod_event=UpdateModEvent(*mod, ensure_account),
            publish_mod_event=PublishModEvent(*mod, ensure_account, SqlActiveCategories(sessions)),
            unpublish_mod_event=UnpublishModEvent(*mod, ensure_account),
            cancel_mod_event=CancelModEvent(*mod, ensure_account),
            delete_mod_event=DeleteModEvent(*mod, ensure_account),
            relay_outbox=RelayOutbox(outbox, ArqEventQueue(arq_redis)),
            handle_domain_event=HandleDomainEvent(
                cache,
                SqlEventFavorites(sessions),
                process_image,
                delete_image_files,
                run_ai_search,
                notify_for_domain_event,
            ),
            purge_outbox=PurgeOutbox(outbox),
            storage=storage,
            image_urls=image_urls,
            create_upload=CreateUpload(*mod, ensure_account, images, storage),
            attach_image=AttachImage(*mod, images, cache, ensure_account, storage),
            order_images=OrderImages(*mod, images, cache),
            remove_image=RemoveImage(*mod, images, cache),
            retry_image=RetryImage(*mod, images, cache, storage),
            process_image=process_image,
            purge_images=PurgeImages(images, storage),
            list_mod_categories=ListModCategories(categories),
            create_category=CreateCategory(categories),
            update_category=UpdateCategory(categories),
            order_categories=OrderCategories(categories),
            delete_category=DeleteCategory(categories),
            ai_http=ai_http,
            start_ai_search=StartAiSearch(ai_jobs, ensure_account, geocoding, clock, ai_settings),
            get_ai_search=GetAiSearch(ai_jobs, ensure_account),
            list_ai_searches=ListAiSearches(ai_jobs, ensure_account),
            run_ai_search=run_ai_search,
            fail_stuck_searches=FailStuckSearches(ai_jobs, ai_settings),
            compact_ai_search_logs=CompactAiSearchLogs(ai_jobs),
            ai_parts=ai_parts,
            push_http=push_http,
            push_provider=sender.provider,
            list_notifications=ListNotifications(notifications, ensure_account),
            mark_notification_read=MarkNotificationRead(notifications, ensure_account),
            mark_all_notifications_read=MarkAllNotificationsRead(notifications, ensure_account),
            delete_notification=DeleteNotification(notifications, ensure_account),
            get_notification_settings=GetNotificationSettings(
                notification_settings, ensure_account
            ),
            update_notification_settings=UpdateNotificationSettings(
                notification_settings, ensure_account, geocoding
            ),
            register_device=RegisterDevice(devices, ensure_account),
            remove_device=RemoveDevice(devices, ensure_account),
            push_notifications=PushNotifications(
                notifications, notification_settings, devices, sender, push_jobs
            ),
            check_push_receipts=CheckPushReceipts(sender, devices),
            send_reminders=SendReminders(recipients, notify, clock),
            purge_notifications=PurgeNotifications(notifications, devices),
        )

    async def aclose(self) -> None:
        """Release all resources."""
        if self.http is not None:
            await self.http.aclose()
        await self.auth_http.aclose()
        await self.storage.aclose()
        for client in [*self.ai_http, *self.push_http]:
            await client.aclose()
        await self.arq_redis.aclose()
        await self.redis.aclose()
        await self.engine.dispose()


def _ai_adapters(
    settings: Settings, clients: list[httpx.AsyncClient]
) -> tuple[EventFinder, WebSearchPort, SourceChecker, PageReader | None]:
    """LLM, web search, source check and page reader as configured (fail fast: `Settings`)."""
    finder: EventFinder
    if settings.llm_provider is LlmProvider.FAKE:
        finder = FakeEventFinder()
    else:
        finder = PydanticAiEventFinder(
            build_model(
                LlmConfig(
                    kind=LlmKind(settings.llm_provider.value),
                    model=settings.llm_model,
                    api_key=(
                        settings.llm_api_key.get_secret_value() if settings.llm_api_key else None
                    ),
                    base_url=str(settings.llm_base_url) if settings.llm_base_url else None,
                )
            )
        )
    search: WebSearchPort
    sources: SourceChecker
    pages: PageReader | None
    if settings.web_search_provider is WebSearchProvider.SEARXNG and settings.web_search_base_url:
        # SearXNG asks several engines per query; it answers slower than an API.
        search_client = httpx.AsyncClient(timeout=20.0)
        source_client = create_source_client()
        clients.extend([search_client, source_client])
        search = SearxngWebSearch(search_client, str(settings.web_search_base_url))
        sources = HttpSourceChecker(source_client)
        pages = HttpPageReader(source_client)
    elif settings.web_search_provider is WebSearchProvider.BRAVE and settings.web_search_api_key:
        search_client = httpx.AsyncClient(timeout=10.0)
        source_client = create_source_client()
        clients.extend([search_client, source_client])
        search = BraveWebSearch(search_client, settings.web_search_api_key.get_secret_value())
        sources = HttpSourceChecker(source_client)
        pages = HttpPageReader(source_client)
    else:
        # The fake search returns example pages that do not exist (dev/test only).
        search = FakeWebSearch()
        sources = AllowAllSourceChecker()
        pages = None
    return finder, search, sources, pages


def _push_sender(settings: Settings, clients: list[httpx.AsyncClient]) -> PushSender:
    """Push adapter for `PUSH_PROVIDER` (credentials checked by `Settings`)."""
    match settings.push_provider:
        case PushProvider.EXPO:
            client = httpx.AsyncClient(timeout=10.0)
            clients.append(client)
            return ExpoPushSender(client, _secret(settings.expo_access_token))
        case PushProvider.DIRECT:
            assert settings.apns_key_path is not None  # noqa: S101
            assert settings.fcm_credentials_path is not None  # noqa: S101
            # APNs only accepts HTTP/2.
            client = httpx.AsyncClient(timeout=10.0, http2=True)
            clients.append(client)
            return DirectPushSender(
                client,
                ApnsConfig.from_file(
                    settings.apns_key_id or "",
                    settings.apns_team_id or "",
                    settings.apns_key_path,
                    settings.apns_topic,
                    sandbox=settings.apns_sandbox,
                ),
                FcmConfig.from_file(settings.fcm_project_id or "", settings.fcm_credentials_path),
            )
        case PushProvider.DISABLED:
            return DisabledPushSender()
