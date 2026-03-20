import re

with open("quickstart.ps1", "r") as f:
    text = f.read()

text = text.replace(
    '''    } elseif ($SubscriptionMode -eq "minimax_code") {
        Write-Ok "MiniMax Coding Key -> $SelectedModel"
        Write-Color -Text "  API: api.minimax.io/v1 (OpenAI-compatible)" -Color DarkGray
    } elseif ($SubscriptionMode -eq "minimax_code") {''',
    '''    } elseif ($SubscriptionMode -eq "minimax_code") {'''
)

with open("quickstart.ps1", "w") as f:
    f.write(text)
