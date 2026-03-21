module.exports = {
  code: `
$addContainer[
$addTextDisplay[# Help - CMDS]
$addSeparator
$addTextDisplay[## **Slash Commands:**
- /help (Shows this message)
- /set_verification_role (REQUIRED FOR VERIFICATION, OWNER ONLY, set a role for the user to get when the user finishes verifying)
- /members (ADMINS ONLY, shows every verified members, only the specified member will be shown if the option is specified)
- /welcome (ADMINS ONLY, read autocomplete)
## **Prefix Commands: (.)**
- .up (OWNER ONLY, updates all cmds)
- .exe (OWNER ONLY, evals a specified command)
$c[- .verify (Verify yourself on the current server)]
$ephemeral
		]
		]    
  `,
  data: {
    name: "help",
    description: "See all commands and what they do (includes prefix commands).",
    options: [
      {
        name: "command",
        description: "Command to show help for.",
        type: 3, // STRING
        required: false
      }
    ]
  }
};