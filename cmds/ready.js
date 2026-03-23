module.exports = {
    type: "clientReady",
    code: `$log[ready]
    $setInterval[$setStatus[$guildCount servers;Watching;$guildCount servers and $userCount members.];3m;status]`
}