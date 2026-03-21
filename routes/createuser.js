module.exports = {
    url: "/api/user/create",
    method: "POST",
    code: `
$let[body;$jsonParse[$requestBody]]
$let[response;$httpFetch[https://$env[PTERO_URL]/api/application/users;{
    "method": "POST",
    "headers": {
        "Authorization": "Bearer $env[PTERO_ADMIN_KEY]",
        "Content-Type": "application/json",
        "Accept": "application/json"
    },
    "body": {
        "email": "$jsonGet[$get[body];email]",
        "username": "$jsonGet[$get[body];username]",
        "first_name": "$jsonGet[$get[body];first_name]",
        "last_name": "$jsonGet[$get[body];last_name]",
        "password": "$jsonGet[$get[body];password]"
    }
}]]
$sendJson[$get[response]]
    `
};