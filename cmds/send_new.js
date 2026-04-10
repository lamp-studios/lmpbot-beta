module.exports = {
    name: "send_new",
    type: "messageCreate",
    code: `
$onlyForUsers[;1056952213056004118]
$jsonLoad[records;$searchDB[news_channel;;guild]]
$arrayForEach[records;record;
    $sendMessage[$env[record;value];$eval[$message;false]]
]
    `
}
