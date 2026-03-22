import os
from firecrawl import FirecrawlApp
from pydantic import BaseModel, Field
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# 1. Define your structure using Pydantic
class WebsiteCapabilities(BaseModel):
    site_name: str = Field(description="The name of the website")
    core_capabilities: List[str] = Field(description="A clean list of core features and capabilities")
    value_proposition: str = Field(description="A single paragraph summarizing what this site does for users")

# 2. Initialize Firecrawl (ensure your API key is in .env or os.environ)
# Look for 'FIRECRAWL_API_KEY'
api_key = os.getenv("FIRECRAWL_API_KEY")
if not api_key:
    raise ValueError("FIRECRAWL_API_KEY not found. Please set it in a .env file or environment variable.")

app = FirecrawlApp(api_key=api_key)

def get_capabilities_md(url: str, output_file: str = "capabilities.md"):
    print(f"🔍 Analyzing capabilities for {url}...")
    
    # 3. Use Firecrawl's extract mode with your Pydantic schema
    scrape_result = app.scrape_url(
        url,
        params={
            "formats": ["json"],
            "jsonOptions": {
                "prompt": "Extract the core capabilities and features. Ignore navigation links and ads.",
                "schema": WebsiteCapabilities.model_json_schema()
            }
        }
    )

    # Note: Firecrawl's Python SDK result might have 'json' directly or inside 'data'
    data = scrape_result.get("json", {})
    if not data:
        print("⚠️ No data extracted. Check if the URL is correct or try a different one.")
        return

    # 4. Generate the Markdown content
    markdown_content = f"# Capabilities of {data.get('site_name', 'Website')}\n\n"
    markdown_content += f"> {data.get('value_proposition', 'No summary available.')}\n\n"
    markdown_content += "## 🚀 Core Features\n\n"
    for cap in data.get("core_capabilities", []):
        markdown_content += f"- {cap}\n"

    # 5. Save to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    
    print(f"✅ Capabilities saved to '{output_file}'!")

if __name__ == "__main__":
    import sys
    # If a URL is passed via command line, use it
    if len(sys.argv) > 1:
        target_url = sys.argv[1]
    else:
        # Default fallback (user can change this)
        target_url = "https://www.firecrawl.dev"
    
    get_capabilities_md(target_url)
