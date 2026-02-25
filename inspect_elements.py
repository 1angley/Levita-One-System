import asyncio
from playwright.async_api import async_playwright
import os

async def inspect_page():
    async with async_playwright() as p:
        user_data_dir = os.path.join(os.getcwd(), "user_data")
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            slow_mo=500
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        timesheet_url = "https://transformukconsulting2.lightning.force.com/lightning/n/KimbleOne__MyTimesheet"
        
        print(f"Opening {timesheet_url}...")
        await page.goto(timesheet_url)
        
        print("Please log in and navigate to the timesheet if not already there.")
        print("The script will periodically scan for elements and print them.")
        
        try:
            with open("elements_log.txt", "w", encoding="utf-8") as log_file:
                while True:
                    # Check for iframes, as Kimble usually lives in one
                    frames = page.frames
                    status_msg = f"\n--- Current state: {len(frames)} frames found ---"
                    print(status_msg)
                    log_file.write(status_msg + "\n")
                    
                    for i, frame in enumerate(frames):
                        try:
                            # Try to get some info from the frame
                            title = await frame.title()
                            frame_info = f"Frame {i} [{frame.name}]: Title='{title}', URL='{frame.url[:60]}...'"
                            print(frame_info)
                            log_file.write(frame_info + "\n")
                            
                            # Look for common buttons or inputs in this frame
                            buttons = await frame.query_selector_all("button, input[type='button'], .btn, a")
                            if buttons:
                                # Filter for buttons that might be relevant to Azure login
                                azure_buttons = []
                                for b in buttons:
                                    try:
                                        text = await b.inner_text()
                                        if "azure" in text.lower():
                                            azure_buttons.append(b)
                                    except:
                                        continue
                            
                                if azure_buttons:
                                    print(f"  *** Found {len(azure_buttons)} potential Azure login buttons! ***")
                                    for b in azure_buttons:
                                        text = await b.inner_text()
                                        val = await b.get_attribute("value")
                                        id_attr = await b.get_attribute("id")
                                        btn_info = f"    - AZURE Button: text='{text.strip()}', id='{id_attr}', value='{val}'"
                                        print(btn_info)
                                        log_file.write(btn_info + "\n")

                                print(f"  Found {len(buttons)} total buttons/inputs/links.")
                                log_file.write(f"  Found {len(buttons)} total buttons/inputs/links.\n")
                                for b in buttons[:10]: # Show first 10
                                    text = await b.inner_text()
                                    val = await b.get_attribute("value")
                                    btn_info = f"    - Button/Link: text='{text.strip()}', value='{val}'"
                                    print(btn_info)
                                    log_file.write(btn_info + "\n")
                                    
                            inputs = await frame.query_selector_all("input[type='text'], input:not([type]), select")
                            if inputs:
                                input_count = f"  Found {len(inputs)} text inputs/selects."
                                print(input_count)
                                log_file.write(input_count + "\n")
                                for inp in inputs[:10]:
                                    name = await inp.get_attribute("name")
                                    id_attr = await inp.get_attribute("id")
                                    input_info = f"    - Input: name='{name}', id='{id_attr}'"
                                    print(input_info)
                                    log_file.write(input_info + "\n")
                                
                        except Exception as e:
                            err_msg = f"  Could not inspect frame {i}: {e}"
                            print(err_msg)
                            log_file.write(err_msg + "\n")
                    
                    log_file.flush() # Ensure it writes to disk
                    print("\nWaiting 10 seconds before next scan (Ctrl+C to stop)...")
                    await asyncio.sleep(10)
        except KeyboardInterrupt:
            print("Stopping inspection.")
        except Exception as e:
            print(f"Inspection error: {e}")
        finally:
            await context.close()

if __name__ == "__main__":
    asyncio.run(inspect_page())
