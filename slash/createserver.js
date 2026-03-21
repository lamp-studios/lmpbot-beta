module.exports = {
    code: `
$let[response;$httpFetch[http://localhost:3000/api/server/create{
    "method": "POST",
    "headers": {"Content-Type": "application/json"},
    "body": {
        "name": "$option[name]",
        "user_id": $option[user_id],
        "egg_id": $option[egg],
        "memory": 1024,
        "disk": 1024,
        "cpu": 3,
        "allocation_id": 1
    }
}]]
✅ Server **$option[name]** created!
📋 Memory: 1024MiB | Disk: 1024MiB | CPU: 3%
$ephemeral
    `,
    data: {
        name: "createserver",
        description: "Create a new game server on the panel.",
        options: [
            {
                name: "name",
                description: "Server name",
                type: 3,
                required: true
            },
            {
                name: "user_id",
                description: "Panel user ID to own the server",
                type: 4,
                required: true
            },
            {
                name: "egg",
                description: "Egg ID (game type)",
                type: 4,
                required: true
            }
        ]
    }
};