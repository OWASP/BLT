/**
 * Determines if a comment was made by a human user.
 * `@param` {object} comment - GitHub comment object
 * `@returns` {boolean} true if commenter is a User or Mannequin (imported account)
 */
function isHumanCommenter(comment) {
    return (
        comment &&
        comment.user &&
        (comment.user.type === 'User' || comment.user.type === 'Mannequin')
    );
}

/**
 * Safely extracts user login and type from a comment.
 * `@param` {object} comment - GitHub comment object
 * `@returns` {{login: string, type: string}} user info with "unknown" defaults
 */
function extractUserInfo(comment) {
    const login = comment?.user?.login ?? "unknown";
    const type = comment?.user?.type ?? "unknown";
    return { login, type };
}

module.exports = { isHumanCommenter, extractUserInfo };