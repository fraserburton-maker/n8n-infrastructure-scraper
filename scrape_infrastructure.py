import os
import json
from typing import List
from pydantic import BaseModel, Field
from firecrawl import FirecrawlApp
try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    console = Console()
except ImportError:
    console = None

# Initialize Firecrawl (Using key found in mcp_config)
API_KEY = "fc-4e7471a2e101486996f41c9227f6890e"
app = FirecrawlApp(api_key=API_KEY)

# 2. Define Structured Data Schema
class InfrastructureUseCase(BaseModel):
    industry: str = Field(description="One of: Utilities, AEC, Rail, Ports, Airports")
    capability_name: str = Field(description="The GIS/Technical capability (e.g. Digital Twin)")
    use_case: str = Field(description="Description of the specific project/application")
    business_value: str = Field(description="The outcome (e.g. 20% efficiency gain)")

class ScrapeResult(BaseModel):
    results: List[InfrastructureUseCase]

# 3. Targeted URLs
urls = [
    "https://www.esri.com/en-us/industries/infrastructure-management/overview",
    "https://esriaustralia.com.au/industries",
    "https://www.udcus.com/spotlight-projects/"
]

def run_extraction():
    raw_results = []
    
    if console:
        console.print("[bold blue]🚀 Starting Infrastructure Geospatial Scraper (v4.x compatible)...[/bold blue]")
    else:
        print("Starting Infrastructure Geospatial Scraper (v4.x compatible)...")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) if console else open(os.devnull, "w") as progress:
        
        task = None
        if console:
            task = progress.add_task(description="Processing URLs...", total=len(urls))
            
        for url in urls:
            if console:
                progress.update(task, description=f"🔍 Scraping: {url}")
            else:
                print(f"🔍 Scraping: {url}")
                
            try:
                # Scrape with latest 4.x arguments
                response = app.scrape(
                    url,
                    formats=["json"],
                    json_options={
                        "schema": ScrapeResult.model_json_schema()
                    },
                    only_main_content=True
                )
                
                # In 4.x, the response usually has a 'data' key which contains 'json'
                if response and response.get("success"):
                    data = response.get("data", {})
                    extracted_json = data.get("json", {})
                    results = extracted_json.get("results", [])
                    raw_results.extend(results)
                    if console:
                        console.print(f"  [green]✅ Found {len(results)} items from {url}[/green]")
                    else:
                        print(f"  ✅ Found {len(results)} items from {url}")
                else:
                    if console:
                        console.print(f"  [yellow]⚠️ No data returned for {url}. Response: {list(response.keys()) if response else 'None'}[/yellow]")
                    else:
                        print(f"  ⚠️ No data returned for {url}")
            except Exception as e:
                if console:
                    console.print(f"  [red]❌ Error on {url}: {e}[/red]")
                else:
                    print(f"  ❌ Error on {url}: {e}")
            
            if console:
                progress.advance(task)

    # 4. Deduplication Logic
    seen_fingerprints = set()
    unique_data = []
    
    for item in raw_results:
        # Create a fingerprint from industry, type, and first part of use case
        fingerprint = f"{item['industry']}-{item['capability_name']}-{item['use_case'][:50]}".lower().strip()
        if fingerprint not in seen_fingerprints:
            seen_fingerprints.add(fingerprint)
            unique_data.append(item)

    dupes_removed = len(raw_results) - len(unique_data)
    if console:
        console.print(f"[bold cyan]✨ Data Processing Complete: removed {dupes_removed} duplicates.[/bold cyan]")
    else:
        print(f"Data Processing Complete: removed {dupes_removed} duplicates.")

    # 5. Write to Markdown
    output_file = "infrastructure_capabilities.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# 🏗️ Infrastructure Geospatial Capabilities Report\n\n")
        f.write(f"*Generated on: 2026-03-22*\n\n")
        f.write("> This report summarizes digital twin and GIS capabilities across various infrastructure domains.\n\n")
        
        if not unique_data:
            f.write("⚠️ No data was successfully extracted from the sources.\n")
        else:
            f.write("| Industry | Capability | Use Case | Business Value |\n")
            f.write("| :--- | :--- | :--- | :--- |\n")
            
            for item in unique_data:
                # Escape pipes in content for MD table compatibility
                ind = str(item.get('industry', '')).replace("|", "\\|")
                cap = str(item.get('capability_name', '')).replace("|", "\\|")
                use = str(item.get('use_case', '')).replace("|", "\\|")
                val = str(item.get('business_value', '')).replace("|", "\\|")
                f.write(f"| {ind} | {cap} | {use} | {val} |\n")

    if console:
        console.print(f"\n[bold green]🚀 Report generated successfully: {output_file}[/bold green]")
        if unique_data:
            table = Table(title="Extracted Capabilities Summary (First 10)")
            table.add_column("Industry", style="cyan")
            table.add_column("Capability", style="magenta")
            table.add_column("Use Case", style="white")
            for item in unique_data[:10]:
                table.add_row(str(item.get('industry', '')), str(item.get('capability_name', '')), str(item.get('use_case', ''))[:70] + "...")
            console.print(table)
    else:
        print(f"Report generated: {os.path.abspath(output_file)}")

if __name__ == "__main__":
    run_extraction()
