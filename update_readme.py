with open("examples/templates/README.md", "r") as f:
    content = f.read()

new_row = "| [commercial_crm_agent](commercial_crm_agent/) | Zero-Glue-Code Revenue/Support Agent that searches CRMs for leads/deals and dispatches messaging notifications |\n"

lines = content.splitlines()
idx = lines.index("| [tech_news_reporter](tech_news_reporter/) | Researches the latest technology and AI news from the web and produces a well-organized report |")

lines.insert(idx + 1, new_row.strip())

with open("examples/templates/README.md", "w") as f:
    f.write("\n".join(lines) + "\n")
