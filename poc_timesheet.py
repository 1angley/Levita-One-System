import asyncio
from playwright.async_api import async_playwright
import os
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv()
AZURE_EMAIL = os.getenv("AZURE_EMAIL")
AZURE_PASSWORD = os.getenv("AZURE_PASSWORD")

async def handle_azure_login(page):
    """Handles the Microsoft/Azure login flow once the initial button is clicked."""
    try:
        print("Looking for Microsoft login fields...")
        
        # Check if we are already logged in or if the Microsoft page appeared
        try:
            # Wait for either the email field OR the timesheet to load (meaning we were already in)
            await page.wait_for_selector("input[type='email'], input[name='loginfmt'], .oneCenterStage", timeout=15000)
            if await page.query_selector(".oneCenterStage"):
                print("Redirected to Salesforce already - skipping Azure automation.")
                return
        except:
            pass

        # 1. Enter Email
        email_selector = "input[type='email'], input[name='loginfmt']"
        await page.wait_for_selector(email_selector, timeout=10000)
        await page.fill(email_selector, AZURE_EMAIL)
        await page.click("input[type='submit'], #idSIButton9")
        
        # 2. Enter Password
        password_selector = "input[type='password'], input[name='passwd']"
        await page.wait_for_selector(password_selector, timeout=10000)
        await asyncio.sleep(1) # Small delay for transition
        await page.fill(password_selector, AZURE_PASSWORD)
        await page.click("input[type='submit'], #idSIButton9")
        
        # 3. Handle 'Stay signed in?' prompt if it appears
        try:
            stay_signed_in_selector = "text='Stay signed in?', #idSIButton9"
            # Short timeout as this might not appear
            await page.wait_for_selector("#idSIButton9", timeout=5000)
            print("Confirming 'Stay signed in'...")
            await page.click("#idSIButton9")
        except:
            print(" 'Stay signed in' prompt did not appear or was missed.")

    except Exception as e:
        print(f"Note: Azure login flow interrupted or skipped: {e}")
        print("Continuing to monitor for timesheet load...")

async def run_poc():
    async with async_playwright() as p:
        # We use a user data dir to persist login state if needed
        user_data_dir = os.path.join(os.getcwd(), "user_data")
        
        # Launching with a persistent context so the user can login manually once
        # and stay logged in for subsequent runs.
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False, # We need to see what's happening
            slow_mo=500     # Slow down actions so we can observe
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        
        timesheet_url = "https://transformukconsulting2.lightning.force.com/lightning/n/KimbleOne__MyTimesheet"
        
        print(f"Navigating to {timesheet_url}...")
        await page.goto(timesheet_url)
        
        # Give the page a moment to settle and determine where we are
        await asyncio.sleep(5)
        print(f"Current URL: {page.url}")

        # Expanded login check: URL patterns OR presence of login elements
        is_login_page = any(pattern in page.url.lower() for pattern in ["login", "idp", "salesforce.com"])
        
        # Fallback: check if the Azure button is visible even if the URL looks "normal"
        if not is_login_page:
            for frame in page.frames:
                try:
                    btn = await frame.get_by_text("Log in with Azure").is_visible()
                    if btn:
                        print("Login button detected via content (even though URL didn't match).")
                        is_login_page = True
                        break
                except:
                    continue

        if is_login_page:
            print("Login page/prompt detected.")
            
            # Try to click "Log in with Azure" if it exists (searching in all frames)
            try:
                azure_button_selectors = [
                    "text='Log in with Azure'",
                    "text='Login with Azure'",
                    "text='Azure'",
                    "button:has-text('Azure')",
                    "a:has-text('Azure')",
                    "button:has-text('Log in')",
                    ".sso-button",
                    "#idp_section_buttons button",
                    "id='azure_login_button'", # Just in case it has a likely ID
                ]
                
                button_found = False
                
                # Search across all frames
                for frame in page.frames:
                    print(f"Searching for Azure button in frame: {frame.name or 'main'} ({frame.url[:50]}...)")
                    
                    # Method 1: Try with Playwright's get_by_text (very powerful)
                    try:
                        azure_btn = frame.get_by_text("Log in with Azure", exact=True)
                        if await azure_btn.is_visible():
                            print(f"Found Azure button via get_by_text in frame: {frame.name or 'main'}")
                            await azure_btn.scroll_into_view_if_needed()
                            await azure_btn.click()
                            button_found = True
                            await handle_azure_login(page)
                            break
                    except:
                        pass
                        
                    if button_found: break

                    # Method 2: Fallback to specific selectors
                    for selector in azure_button_selectors:
                        try:
                            # Use a very short timeout for each selector check
                            button = await frame.query_selector(selector)
                            if button and await button.is_visible():
                                print(f"Clicking Azure login button using selector: {selector} (in frame: {frame.name or 'main'})")
                                await button.scroll_into_view_if_needed()
                                # Some buttons need a real click simulation or even a dispatchEvent if they are tricky
                                await button.click(force=True) # force=True can bypass overlay issues
                                button_found = True
                                await handle_azure_login(page)
                                break
                        except:
                            continue
                    if button_found:
                        break
                
                if not button_found:
                    print("Azure login button not automatically found. Detailed frame info:")
                    for i, frame in enumerate(page.frames):
                        print(f"Frame {i}: {frame.name or 'main'} - {frame.url[:50]}...")
                        # List elements with 'Azure' in them
                        all_elements = await frame.query_selector_all("a, button, div, span")
                        for el in all_elements:
                            try:
                                txt = await el.inner_text()
                                if "azure" in txt.lower():
                                    print(f"  - POTENTIAL MATCH: Tag={await el.evaluate('e => e.tagName')}, Text='{txt.strip()}'")
                            except:
                                continue
                    print("Please click the Azure login button manually.")
            except Exception as e:
                print(f"Error trying to click Azure button: {e}")

            print("Waiting for manual login completion or redirect...")
            # Wait for navigation away from login page or for a specific element that indicates we are in
            try:
                # Wait up to 5 minutes for manual login/Azure authentication
                await page.wait_for_url("**/lightning/**", timeout=300000)
                print("Login successful or bypassed.")
            except Exception as e:
                print(f"Timed out waiting for login: {e}")
                await context.close()
                return

        # Wait for the timesheet component to load. 
        # Kantata (Kimble) often uses iframes for its timesheet.
        print("Waiting for timesheet page to load...")
        try:
            # Wait for the main Salesforce lightning container
            await page.wait_for_selector(".oneCenterStage", timeout=30000)
            print("Salesforce stage loaded.")
            
            # Since I don't have the exact selectors, I'll search for common Kimble/Kantata elements
            # or wait for any iframe which is common for Kimble.
            await asyncio.sleep(10) # Give it extra time for the iframe to load its contents
            
            # Log frames to help debug
            frames = page.frames
            print(f"Found {len(frames)} frames on the page.")
            
            # --- Targeted Frame Detection for Kimble ---
            timesheet_frame = None
            for frame in frames:
                if "kimbleone" in frame.url.lower() or "visualforce" in frame.url.lower():
                    print(f"Detected likely timesheet frame: {frame.name or 'Unnamed'} - {frame.url[:80]}...")
                    timesheet_frame = frame
                    break
            
            if not timesheet_frame:
                print("Could not identify the specific timesheet frame. Scanning all frames as fallback.")

            # Proof of concept action: take a screenshot
            await page.screenshot(path="timesheet_loaded.png")
            print("Screenshot saved as timesheet_loaded.png")
            
            # --- New Action: Click the "Add Time Entry" button for Monday ---
            print("Attempting to find and click the 'Add Time Entry' button for Monday...")
            
            monday_clicked = False
            
            # We will scan all frames to be safe, as the ID might change
            for frame in page.frames:
                try:
                    # Filter for likely timesheet frames to reduce noise, but don't strictly exclude
                    is_likely_frame = "kimbleone" in frame.url.lower() or "visualforce" in frame.url.lower()
                    
                    print(f"Scanning frame: {frame.name or 'Unnamed'} ({frame.url[:60]}...) [Likely: {is_likely_frame}]")
                    
                    # 1. Broad search for anything with the title '+ Time Entry'
                    # We use an exact title match to avoid 'Start a Timer' or other nearby elements
                    all_targets = await frame.query_selector_all("*[title='+ Time Entry']")
                    print(f"  Found {len(all_targets)} elements with title '+ Time Entry' in this frame.")
                    
                    if len(all_targets) > 0:
                        # Sometimes the first few elements are hidden or represent different rows/days.
                        # We'll filter for visible ones and those NOT containing 'Timer'
                        valid_targets = []
                        for t in all_targets:
                            try:
                                is_visible = await t.is_visible()
                                title = await t.get_attribute("title")
                                text = await t.inner_text()
                                # Double check title is EXACTly '+ Time Entry' to avoid confusion
                                if is_visible and title == "+ Time Entry" and "timer" not in (text.lower() or ""):
                                    valid_targets.append(t)
                            except:
                                continue
                        
                        print(f"  Found {len(valid_targets)} visible/valid '+ Time Entry' targets.")
                        
                        if len(valid_targets) > 0:
                            # In Kimble, the grid usually has 7 buttons per row (Mon-Sun).
                            # Picking the first visible one SHOULD be Monday.
                            target = valid_targets[0]
                            tag_name = await target.evaluate("e => e.tagName")
                            print(f"  Targeting first valid element: {tag_name} (Monday)")
                            
                            await target.scroll_into_view_if_needed()
                            await asyncio.sleep(1)
                            
                            # High-reliability click attempt
                            try:
                                await target.click(timeout=5000)
                                print("  Standard click successful.")
                            except:
                                await target.dispatch_event('click')
                                print("  JS click event dispatched.")
                            
                            monday_clicked = True
                            break
                except Exception as e:
                    print(f"  Error checking frame {frame.name}: {e}")
                    continue
            
            if monday_clicked:
                print("Clicked Monday's Add Time Entry button!")
                # Take a screenshot to verify the dialog opened
                await asyncio.sleep(3)
                await page.screenshot(path="after_monday_click.png")
                print("Screenshot after click saved as after_monday_click.png")
            else:
                print("Could not find the '+ Time Entry' button automatically.")
                # Detailed debug log of what WAS found in the timesheet frame
                if timesheet_frame:
                    print(f"Listing ALL interactive elements in the timesheet frame ({timesheet_frame.name}):")
                    all_interactive = await timesheet_frame.query_selector_all("button, a, span[onclick], div[onclick], .btn")
                    for i, el in enumerate(all_interactive[:40]):
                        txt = (await el.inner_text()).strip()
                        ttl = await el.get_attribute("title")
                        tag = await el.evaluate("e => e.tagName")
                        if txt or ttl:
                            print(f"  [{i}] {tag}: text='{txt}', title='{ttl}'")

        except Exception as e:
            print(f"Error during PoC execution: {e}")
        
        print("PoC finished. Keeping browser open for 30 seconds for observation...")
        await asyncio.sleep(30)
        await context.close()

if __name__ == "__main__":
    asyncio.run(run_poc())
