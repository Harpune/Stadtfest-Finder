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
from stadtfest.adapters.outbound.persistence.accounts import SqlRegionDirectory, SqlUserRepository
from stadtfest.adapters.outbound.persistence.catalog import SqlCatalog
from stadtfest.adapters.outbound.persistence.database import DatabaseProbe, create_engine
from stadtfest.adapters.outbound.persistence.favorites import SqlFavoriteRepository
from stadtfest.adapters.outbound.persistence.images import SqlImageRepository
from stadtfest.adapters.outbound.persistence.moderation import (
    SqlActiveCategories,
    SqlManagedEventRepository,
    SqlModRegionDirectory,
)
from stadtfest.adapters.outbound.persistence.outbox import SqlEventFavorites, SqlOutboxStore
from stadtfest.adapters.outbound.queue.arq_jobs import (
    ArqAccountJobs,
    ArqEventQueue,
    create_arq_redis,
)
from stadtfest.adapters.outbound.storage.s3 import S3Config, S3ObjectStorage
from stadtfest.adapters.outbound.storage.urls import ImageUrls
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
from stadtfest.application.outbox.use_cases import HandleDomainEvent, PurgeOutbox, RelayOutbox
from stadtfest.bootstrap.settings import GeocodingProvider, IdpAdminProvider, Settings


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
        claim_mapping = ClaimMapping(settings.auth_roles_claim, settings.auth_region_claim)
        users = SqlUserRepository(sessions)
        regions = SqlRegionDirectory(sessions)
        idp_admin = _idp_admin(settings, auth_http)
        arq_redis = create_arq_redis(str(settings.redis_url))
        deleted_accounts = RedisDeletedAccounts(redis)
        favorites = SqlFavoriteRepository(sessions, image_urls)
        images = SqlImageRepository(sessions)
        managed = SqlManagedEventRepository(sessions)
        mod_regions = SqlModRegionDirectory(sessions)
        ensure_account = EnsureAccount(users)
        mod = (managed, mod_regions, clock)
        outbox = SqlOutboxStore(sessions)
        process_image = ProcessImage(images, storage, PillowImageProcessor(), cache)
        delete_image_files = DeleteImageFiles(storage)

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
            get_me=GetMe(users, regions),
            update_me=UpdateMe(users, regions),
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
                cache, SqlEventFavorites(sessions), process_image, delete_image_files
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
        )

    async def aclose(self) -> None:
        """Release all resources."""
        if self.http is not None:
            await self.http.aclose()
        await self.auth_http.aclose()
        await self.storage.aclose()
        await self.arq_redis.aclose()
        await self.redis.aclose()
        await self.engine.dispose()
