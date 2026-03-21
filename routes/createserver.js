module.exports = {
    url: "/api/server/create",
    method: "POST",
    code: `
$let[body;$jsonParse[$requestBody]]
$let[response;$httpFetch[https://$env[PTERO_URL]/api/application/servers;{
    "method": "POST",
    "headers": {
        "Authorization": "Bearer $env[PTERO_ADMIN_KEY]",
        "Content-Type": "application/json",
        "Accept": "application/json"
    },
    "body": {
        "name": "$jsonGet[$get[body];name]",
        "user": $jsonGet[$get[body];user_id],
        "egg": $jsonGet[$get[body];egg_id],
        "docker_image": "ghcr.io/pterodactyl/yolks:java_17",
        "startup": "java -Xms128M -Xmx{{SERVER_MEMORY}}M -jar {{SERVER_JARFILE}}",
        "environment": {
            "SERVER_JARFILE": "server.jar",
            "VANILLA_VERSION": "latest"
        },
        "limits": {
            "memory": $jsonGet[$get[body];memory],
            "swap": 0,
            "disk": $jsonGet[$get[body];disk],
            "io": 500,
            "cpu": $jsonGet[$get[body];cpu]
        },
        "feature_limits": {
            "databases": 1,
            "backups": 2,
            "allocations": 1
        },
        "allocation": {
            "default": $jsonGet[$get[body];allocation_id]
        }
    }
}]]
$sendJson[$get[response]]
    `
};