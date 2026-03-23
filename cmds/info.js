module.exports = {
    type: "messageCreate",
    name: "info",
    code: `$addContainer[
    $addTextDisplay[# Bot Information]
    $addSeparator
    $addTextDisplay[**Ping**: $pingms.]
    $addTextDisplay[**Uptime**: $parseMS[$uptime].]
    $addTextDisplay[**OS**: $os.]
    $addTextDisplay[**RAM/Memory**: $round[$ram].]
    ;$randomColor]`
};