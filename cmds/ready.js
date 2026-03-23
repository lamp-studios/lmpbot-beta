module.exports = {
    type: "clientReady",
    code: `$log[ready]
    $setStatus[$guildCount servers;Watching;$guildCount servers and $userCount members.]
    $setInterval[$setStatus[dnd;Watching;$guildCount servers and $userCount members.];3m;status]`
}