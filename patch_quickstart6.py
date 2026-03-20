import re

with open("quickstart.ps1", "r") as f:
    text = f.read()

text = text.replace(
    'OPENAI_API_KEY    = @{ Name = "OpenAI (GPT)";       Id = "openai" }',
    'OPENAI_API_KEY    = @{ Name = "OpenAI (GPT)";       Id = "openai" }\n    MINIMAX_API_KEY   = @{ Name = "MiniMax";            Id = "minimax" }'
)

text = text.replace(
    'openai      = "gpt-5-mini"',
    'openai      = "gpt-5-mini"\n    minimax     = "MiniMax-M2.5"'
)

text = text.replace(
    '    openai = @(',
    '    minimax = @(\n        @{ Id = "MiniMax-M2.5"; Label = "MiniMax-M2.5 - Frontier reasoning (recommended)"; MaxTokens = 8192; MaxContextTokens = 900000 }\n    )\n    openai = @('
)

text = text.replace(
    '$KimiCredDetected = $false',
    '$MinimaxCredDetected = $false\n$minimaxKey = [System.Environment]::GetEnvironmentVariable("MINIMAX_API_KEY", "User")\nif (-not $minimaxKey) { $minimaxKey = $env:MINIMAX_API_KEY }\nif ($minimaxKey) { $MinimaxCredDetected = $true }\n\n$KimiCredDetected = $false'
)

text = text.replace(
    'elseif ($prevLlm.api_base -and $prevLlm.api_base -like "*api.z.ai*") { $PrevSubMode = "zai_code" }',
    'elseif ($prevLlm.api_base -and $prevLlm.api_base -like "*api.z.ai*") { $PrevSubMode = "zai_code" }\n            elseif ($prevLlm.provider -eq "minimax" -or ($prevLlm.api_base -and $prevLlm.api_base -like "*api.minimax.io*")) { $PrevSubMode = "minimax_code" }'
)

text = text.replace(
    '"codex"       { if ($CodexCredDetected)  { $prevCredValid = $true } }',
    '"codex"       { if ($CodexCredDetected)  { $prevCredValid = $true } }\n        "minimax_code" { if ($MinimaxCredDetected) { $prevCredValid = $true } }'
)

text = text.replace(
    '"codex"       { $DefaultChoice = "3" }',
    '"codex"       { $DefaultChoice = "3" }\n            "minimax_code" { $DefaultChoice = "4" }'
)

text = text.replace(
    '"kimi_code"   { $DefaultChoice = "4" }',
    '"kimi_code"   { $DefaultChoice = "5" }'
)

text = text.replace(
    '"anthropic" { $DefaultChoice = "5" }\n                "openai"    { $DefaultChoice = "6" }\n                "gemini"    { $DefaultChoice = "7" }\n                "groq"      { $DefaultChoice = "8" }\n                "cerebras"  { $DefaultChoice = "9" }\n                "kimi"      { $DefaultChoice = "4" }',
    '"anthropic" { $DefaultChoice = "6" }\n                "openai"    { $DefaultChoice = "7" }\n                "gemini"    { $DefaultChoice = "8" }\n                "groq"      { $DefaultChoice = "9" }\n                "cerebras"  { $DefaultChoice = "10" }\n                "minimax"   { $DefaultChoice = "4" }\n                "kimi"      { $DefaultChoice = "5" }'
)

text = text.replace(
    '# 4) Kimi Code',
    '# 4) MiniMax Coding Key\nWrite-Host "  " -NoNewline\nWrite-Color -Text "4" -Color Cyan -NoNewline\nWrite-Host ") MiniMax Coding Key     " -NoNewline\nWrite-Color -Text "(use your MiniMax coding key)" -Color DarkGray -NoNewline\nif ($MinimaxCredDetected) { Write-Color -Text "  (credential detected)" -Color Green } else { Write-Host "" }\n\n# 5) Kimi Code'
)

text = text.replace(
    'Write-Color -Text "4" -Color Cyan -NoNewline\nWrite-Host ") Kimi Code Subscription     " -NoNewline',
    'Write-Color -Text "5" -Color Cyan -NoNewline\nWrite-Host ") Kimi Code Subscription     " -NoNewline'
)

text = text.replace(
    '# 5-9) API key providers',
    '# 6-10) API key providers'
)

text = text.replace(
    '$num = $idx + 5',
    '$num = $idx + 6'
)

text = text.replace(
    'Write-Color -Text "10" -Color Cyan -NoNewline',
    'Write-Color -Text "11" -Color Cyan -NoNewline'
)

text = text.replace(
    'Enter choice (1-10)',
    'Enter choice (1-11)'
)

text = text.replace(
    '$num -le 10',
    '$num -le 11'
)

text = text.replace(
    '    4 {\n        # Kimi Code Subscription',
    '    4 {\n        # MiniMax Coding Key\n        $SubscriptionMode        = "minimax_code"\n        $SelectedProviderId      = "minimax"\n        $SelectedEnvVar          = "MINIMAX_API_KEY"\n        $SelectedModel           = "MiniMax-M2.5"\n        $SelectedMaxTokens       = 32768\n        $SelectedMaxContextTokens = 900000\n        Write-Host ""\n        Write-Ok "Using MiniMax coding key"\n        Write-Color -Text "  Model: MiniMax-M2.5 | API: api.minimax.io" -Color DarkGray\n    }\n    5 {\n        # Kimi Code Subscription'
)

text = text.replace(
    '{ $_ -ge 5 -and $_ -le 9 } {',
    '{ $_ -ge 6 -and $_ -le 10 } {'
)

text = text.replace(
    '$provIdx = $num - 5',
    '$provIdx = $num - 6'
)

text = text.replace(
    '    10 {\n        Write-Host ""\n        Write-Warn "Skipped. An LLM API key is required to test and use worker agents."',
    '    11 {\n        Write-Host ""\n        Write-Warn "Skipped. An LLM API key is required to test and use worker agents."'
)

minimax_key_logic = """
# For MiniMax Code subscription: prompt for API key with verification + retry
if ($SubscriptionMode -eq "minimax_code") {
    while ($true) {
        $existingMinimax = [System.Environment]::GetEnvironmentVariable("MINIMAX_API_KEY", "User")
        if (-not $existingMinimax) { $existingMinimax = $env:MINIMAX_API_KEY }

        if ($existingMinimax) {
            $masked = $existingMinimax.Substring(0, [Math]::Min(4, $existingMinimax.Length)) + "..." + $existingMinimax.Substring([Math]::Max(0, $existingMinimax.Length - 4))
            Write-Host ""
            Write-Color -Text "  $([char]0x2B22) Current MiniMax key: $masked" -Color Green
            $apiKey = Read-Host "  Press Enter to keep, or paste a new key to replace"
        } else {
            Write-Host ""
            Write-Host "Get your API key from: " -NoNewline
            Write-Color -Text "https://platform.minimax.io/user-center/basic-information/interface-key" -Color Cyan
            Write-Host ""
            $apiKey = Read-Host "Paste your MiniMax API key (or press Enter to skip)"
        }

        if ($apiKey) {
            [System.Environment]::SetEnvironmentVariable("MINIMAX_API_KEY", $apiKey, "User")
            $env:MINIMAX_API_KEY = $apiKey
            Write-Host ""
            Write-Ok "MiniMax API key saved as User environment variable"

            # Health check the new key
            Write-Host "  Verifying MiniMax API key... " -NoNewline
            try {
                $hcResult = & uv run python (Join-Path $ScriptDir "scripts/check_llm_key.py") "minimax" $apiKey "https://api.minimax.io/v1" 2>$null
                $hcJson = $hcResult | ConvertFrom-Json
                if ($hcJson.valid -eq $true) {
                    Write-Color -Text "ok" -Color Green
                    break
                } elseif ($hcJson.valid -eq $false) {
                    Write-Color -Text "failed" -Color Red
                    Write-Warn $hcJson.message
                    [System.Environment]::SetEnvironmentVariable("MINIMAX_API_KEY", $null, "User")
                    Remove-Item -Path "Env:\MINIMAX_API_KEY" -ErrorAction SilentlyContinue
                    Write-Host ""
                    Read-Host "  Press Enter to try again"
                } else {
                    Write-Color -Text "--" -Color Yellow
                    Write-Color -Text "  Could not verify key (network issue). The key has been saved." -Color DarkGray
                    break
                }
            } catch {
                Write-Color -Text "--" -Color Yellow
                Write-Color -Text "  Could not verify key (network issue). The key has been saved." -Color DarkGray
                break
            }
        } elseif (-not $existingMinimax) {
            Write-Host ""
            Write-Warn "Skipped. Add your MiniMax API key later:"
            Write-Color -Text "  [System.Environment]::SetEnvironmentVariable('MINIMAX_API_KEY', 'your-key', 'User')" -Color Cyan
            $SelectedEnvVar     = ""
            $SelectedProviderId = ""
            $SubscriptionMode   = ""
            break
        } else {
            break
        }
    }
}
"""

text = text.replace(
    '# For Kimi Code subscription: prompt for API key with verification + retry',
    minimax_key_logic.strip() + '\n\n# For Kimi Code subscription: prompt for API key with verification + retry'
)

text = text.replace(
    '} elseif ($SubscriptionMode -eq "zai_code") {',
    '} elseif ($SubscriptionMode -eq "minimax_code") {\n        $config.llm["api_base"] = "https://api.minimax.io/v1"\n        $config.llm["api_key_env_var"] = $SelectedEnvVar\n    } elseif ($SubscriptionMode -eq "zai_code") {'
)

text = text.replace(
    '    } elseif ($SubscriptionMode -eq "zai_code") {\n        Write-Ok "ZAI Code Subscription -> $SelectedModel"\n        Write-Color -Text "  API: api.z.ai (OpenAI-compatible)" -Color DarkGray',
    '    } elseif ($SubscriptionMode -eq "minimax_code") {\n        Write-Ok "MiniMax Coding Key -> $SelectedModel"\n        Write-Color -Text "  API: api.minimax.io/v1 (OpenAI-compatible)" -Color DarkGray\n    } elseif ($SubscriptionMode -eq "zai_code") {\n        Write-Ok "ZAI Code Subscription -> $SelectedModel"\n        Write-Color -Text "  API: api.z.ai (OpenAI-compatible)" -Color DarkGray'
)

with open("quickstart.ps1", "w") as f:
    f.write(text)
