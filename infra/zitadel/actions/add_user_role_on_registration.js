/**
 * ZITADEL Action (v1): grant the role `user` of the project `stadtfest` to every new account.
 *
 * The project checks the role assignment on authentication ("Check authorization on
 * Authentication"), so an account without a role cannot log in. Attach this action to
 *   - Flow "Internal Authentication", trigger "Post Creation" (sign-up with e-mail) and
 *   - Flow "External Authentication", trigger "Post Creation" (first login via Apple/Google).
 * Accounts created in the console do not run these flows; grant `user` there by hand.
 *
 * Setup: 00-docs/40-operations/zitadel.md, step 1. The action name in the console must be
 * exactly the function name `add_user_role_on_registration`. Replace PROJECT_ID with the
 * resource ID of the project `stadtfest` (same value as AUTH_AUDIENCE). Nothing personal is
 * read or logged here.
 *
 * @param {object} ctx Action context (unused).
 * @param {object} api Action API; `api.userGrants` holds the grants to create for the user.
 */
function add_user_role_on_registration(ctx, api) {
  const PROJECT_ID = 'REPLACE_WITH_PROJECT_ID';
  const ROLE = 'user';

  // Plain loop: `api.userGrants` comes from Go and may not support Array.prototype.find.
  for (let i = 0; i < api.userGrants.length; i++) {
    const grant = api.userGrants[i];
    if (grant.projectID === PROJECT_ID) {
      // Another action already grants this project: add the role to that grant (one
      // grant per user and project).
      if (grant.roles.indexOf(ROLE) === -1) {
        grant.roles.push(ROLE);
      }
      return;
    }
  }
  api.userGrants.push({projectID: PROJECT_ID, roles: [ROLE]});
}
