module.exports = {
type: "interactionCreate",
code: `
$if[$customID==learnmore;
You pushed the button
$ephemeral
]
`}