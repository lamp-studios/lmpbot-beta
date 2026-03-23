module.exports = {
    type: "messageCreate",
    name: "info",
    code: `$addContainer[
    $addTextDisplay[# Bot Information]
    $addSeparator
    $addTextDisplay[**Ping**: $pingms.]
    $addTextDisplay[**Uptime**: $uptime.]
    $addTextDisplay[**OS**: $os.]
    $addTextDisplay[**RAM/Memory**: $ram.]
    ;$randomColor]`
};