import re

with open("quickstart.ps1", "r") as f:
    text = f.read()

text = text.replace(
    '''    } elseif ($SubscriptionMode -eq "minimax_code") {
        $config.llm["api_base"] = "https://api.minimax.io/v1"
        $config.llm["api_key_env_var"] = $SelectedEnvVar
    } elseif ($SubscriptionMode -eq "minimax_code") {
        Write-Ok "MiniMax Coding Key -> $SelectedModel"
        Write-Color -Text "  API: api.minimax.io/v1 (OpenAI-compatible)" -Color DarkGray
    } elseif ($SubscriptionMode -eq "zai_code") {''',
    '''    } elseif ($SubscriptionMode -eq "minimax_code") {
        Write-Ok "MiniMax Coding Key -> $SelectedModel"
        Write-Color -Text "  API: api.minimax.io/v1 (OpenAI-compatible)" -Color DarkGray
    } elseif ($SubscriptionMode -eq "zai_code") {'''
)

with open("quickstart.ps1", "w") as f:
    f.write(text)
