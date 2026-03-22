module.exports = {
type: "interactionCreate",
code: `
$if[$customID==learnmore;
To automatically ban/kick bots, since most popular discord bots don't have that feature, *yet*. We had to make our own for our server.
$ephemeral
]
`}