module.exports = {
    type: "clientReady",
    code: `$log[ready]
    $setStatus[dnd;Watching;$guildCount servers and $userCount members.]
    $setInterval[$setStatus[dnd;Watching;$guildCount servers and $userCount members.];1m;status]`
}