import asyncio
import os
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# Load credentials
load_dotenv()
AZURE_EMAIL = os.getenv("AZURE_EMAIL")
AZURE_PASSWORD = os.getenv("AZURE_PASSWORD")

class TimesheetAutomation:
    def __init__(self, headless=False):
        self.headless = headless
        self.user_data_dir = os.path.join(os.getcwd(), "user_data")
        self.timesheet_url = "https://transformukconsulting2.lightning.force.com/lightning/n/KimbleOne__MyTimesheet"

    async def handle_azure_login(self, page):
        """Handles the Microsoft/Azure login flow."""
        try:
            print("Looking for Microsoft login fields...", flush=True)
            try:
                # Use a combined selector to detect where we are
                await page.wait_for_selector("input[type='email'], input[name='loginfmt'], input[type='password'], input[name='passwd'], #idSIButton9, .oneCenterStage", timeout=20000)
                if await page.query_selector(".oneCenterStage"):
                    print("Already in Salesforce - skipping login.", flush=True)
                    return
            except Exception as e:
                print(f"Wait for login fields timeout/error: {e}", flush=True)

            # 1. Enter Email if present OR click already listed account
            email_selector = "input[type='email'], input[name='loginfmt']"
            # Microsoft "Pick an account" tiles often have the email text or specific data-test-id
            account_tile_selectors = [
                f"text='{AZURE_EMAIL}'",
                "div[role='listitem']",
                ".table-row",
                "div[data-test-id]",
                "#tilesHolder",
                "div:has-text('Pick an account')"
            ]
            
            try:
                # Wait a bit for either the email input OR the account picker tiles
                await page.wait_for_selector(f"{email_selector}, {', '.join(account_tile_selectors[:4])}", timeout=10000)
            except:
                pass
                
            email_field = await page.query_selector(email_selector)
            if email_field and await email_field.is_visible():
                print(f"Entering email: {AZURE_EMAIL}", flush=True)
                await email_field.fill(AZURE_EMAIL)
                # After filling email, wait a tiny bit before clicking
                await asyncio.sleep(1)
                await page.click("input[type='submit'], #idSIButton9")
                await asyncio.sleep(2)
            else:
                # Check for Account Tiles (Pick an account)
                print("Checking for existing account tiles...", flush=True)
                found_tile = False
                
                # Try the user-provided XPath specifically
                user_xpath = 'xpath=//*[@id="tilesHolder"]/div[1]/div/div[1]/div/div[2]/div'
                try:
                    xpath_tile = await page.wait_for_selector(user_xpath, timeout=5000)
                    if xpath_tile and await xpath_tile.is_visible():
                        print(f"Found account tile via user XPath. Clicking...", flush=True)
                        await xpath_tile.click()
                        found_tile = True
                        await asyncio.sleep(2)
                except:
                    pass
                
                if not found_tile:
                    for selector in account_tile_selectors:
                        try:
                            # Specifically look for the tile with the email text first
                            tile = await page.get_by_text(AZURE_EMAIL).first
                            if await tile.is_visible():
                                print(f"Found account tile with email {AZURE_EMAIL}. Clicking...", flush=True)
                                await tile.click()
                                found_tile = True
                                await asyncio.sleep(2)
                                break
                            
                            # Fallback to other selectors if email text isn't a direct match
                            other_tile = await page.query_selector(selector)
                            if other_tile and await other_tile.is_visible():
                                # Check if it contains the email text
                                inner_text = await other_tile.inner_text()
                                if AZURE_EMAIL.lower() in inner_text.lower():
                                    print(f"Found tile matching {AZURE_EMAIL} via selector {selector}. Clicking...", flush=True)
                                    await other_tile.click()
                                    found_tile = True
                                    await asyncio.sleep(2)
                                    break
                        except:
                            continue
                
                if not found_tile:
                    print("Email field not visible and no matching account tile found.", flush=True)
                    # Last resort: click anything in #tilesHolder if it exists
                    try:
                        first_tile = await page.query_selector("#tilesHolder .tile, #tilesHolder div[role='listitem']")
                        if first_tile and await first_tile.is_visible():
                            print("Clicking first available tile in #tilesHolder as fallback...", flush=True)
                            await first_tile.click()
                            found_tile = True
                            await asyncio.sleep(2)
                    except:
                        pass

            # 2. Enter Password
            password_selector = "input[type='password'], input[name='passwd']"
            try:
                await page.wait_for_selector(password_selector, timeout=15000)
                print("Entering password...", flush=True)
                await page.fill(password_selector, AZURE_PASSWORD)
                # Use a more explicit wait for the button to be enabled/clickable
                submit_button = "input[type='submit'], #idSIButton9"
                await page.wait_for_selector(submit_button)
                await page.click(submit_button)
                await asyncio.sleep(2)
            except Exception as e:
                print(f"Password field not found or error: {e}", flush=True)
            
            # 3. Handle 'Stay signed in?' or other intermediate prompts
            for _ in range(3): # Try a few times for different prompts
                try:
                    # Look for any submit button that might be "Stay signed in" or "Next"
                    stay_btn = await page.wait_for_selector("#idSIButton9, input[type='submit']", timeout=5000)
                    if stay_btn and await stay_btn.is_visible():
                        print("Clicking intermediate button (Stay signed in / Next)...", flush=True)
                        await stay_btn.click()
                        await asyncio.sleep(2)
                    else:
                        break
                except:
                    break

        except Exception as e:
            print(f"Azure login flow error: {e}", flush=True)
            # Take a screenshot for debugging if it stalls
            try:
                await page.screenshot(path="azure_login_stall.png")
                print("Screenshot saved as azure_login_stall.png", flush=True)
            except:
                pass

    async def get_current_week_start(self, frame_or_page):
        """Extracts the current week start date from the Kimble header by scanning all frames."""
        try:
            # The header format the user specifically mentioned:
            # "Alex Langley - Mar / 2 / 2026 (02/03/2026 to 08/03/2026)"
            # We need to find the frame that contains this text.
            
            target_text_pattern = "Alex Langley - "
            frames_to_scan = []
            if hasattr(frame_or_page, "frames"): # It's a Page
                frames_to_scan = frame_or_page.frames
            else: # It's a Frame, but we might want to scan all sibling/parent frames too if it's not here
                frames_to_scan = frame_or_page.page.frames
                
            header_text = None
            found_frame = None
            
            for f in frames_to_scan:
                try:
                    # Check for the specific container first
                    container = f.locator("#fixed-header-container")
                    if await container.is_visible():
                        header_text = await container.inner_text()
                        if target_text_pattern in header_text:
                            found_frame = f
                            print(f"Found header in frame: {f.name or 'main'} via #fixed-header-container", flush=True)
                            break
                    
                    # If not in container, try searching for the text anywhere in the frame
                    content = await f.content()
                    if target_text_pattern in content:
                        # Find the actual element containing it for better extraction
                        # Kimble often uses specific classes for headers
                        potential_headers = await f.locator(f"text='{target_text_pattern}'").all()
                        for ph in potential_headers:
                            txt = await ph.inner_text()
                            if target_text_pattern in txt:
                                header_text = txt
                                found_frame = f
                                print(f"Found header text in frame: {f.name or 'main'}: '{header_text.strip()}'", flush=True)
                                break
                        if found_frame: break
                except:
                    continue

            if not header_text:
                print(f"Could not find header containing '{target_text_pattern}' in any frame.", flush=True)
                return None

            import re
            # Try parsing the (dd/mm/yyyy to dd/mm/yyyy) part if it exists
            match = re.search(r"\((\d{1,2}/\d{1,2}/\d{4}) to", header_text)
            if match:
                date_str = match.group(1)
                return datetime.strptime(date_str, "%d/%m/%Y").date()
            
            # Fallback to the "MMM / d / yyyy" format the user specifically mentioned
            # Example: "Mar / 2 / 2026"
            match_alt = re.search(r"([A-Z][a-z]{2}) / (\d{1,2}) / (\d{4})", header_text)
            if match_alt:
                month_name, day_num, year_num = match_alt.groups()
                return datetime.strptime(f"{month_name} {day_num} {year_num}", "%b %d %Y").date()
                
            print(f"Could not parse date from header text: {header_text}", flush=True)
        except Exception as e:
            print(f"Error extracting week date: {e}", flush=True)
        return None

    async def navigate_to_week(self, page, target_date):
        """Navigates to the specified week start date using Next/Previous buttons."""
        max_attempts = 10
        for _ in range(max_attempts):
            current_date = await self.get_current_week_start(page)
            if not current_date:
                print("Cannot determine current week date - skipping navigation.", flush=True)
                return False
                
            print(f"Currently on week: {current_date}. Target: {target_date}.", flush=True)
            
            if current_date == target_date:
                print("Correct week reached.", flush=True)
                return True
            
            # We need to find the frame with the buttons again
            btn_frame = None
            for f in page.frames:
                try:
                    if await f.locator("#fixed-header-container").is_visible():
                        btn_frame = f
                        break
                except: continue
            
            if not btn_frame:
                print("Could not find frame with navigation buttons.", flush=True)
                return False

            if current_date > target_date:
                print("Clicking 'Previous Period'...", flush=True)
                await btn_frame.locator("#fixed-header-container").get_by_title("Previous Period").click()
            else:
                print("Clicking 'Next Period'...", flush=True)
                await btn_frame.locator("#fixed-header-container").get_by_title("Next Period").click()
                
            # Wait for the page to refresh after clicking
            await asyncio.sleep(3)
            
        print(f"Failed to reach target week after {max_attempts} attempts.", flush=True)
        return False

    async def run_sync(self, week_start_date, day_hours, activity_type=None):
        """
        week_start_date: datetime.date (Monday)
        day_hours: list of 7 floats [Mon, Tue, Wed, Thu, Fri, Sat, Sun]
        activity_type: string representing the Salesforce activity code/name
        """
        async with async_playwright() as p:
            # Check if user data dir is locked
            lock_file = os.path.join(self.user_data_dir, "SingletonLock")
            if os.path.exists(lock_file):
                print(f"WARNING: {self.user_data_dir} appears to be locked. This might be why it stalls.", flush=True)
                # We could try to remove it if we are SURE no other playwright is running, 
                # but Playwright usually handles this or fails.
            
            try:
                context = await p.chromium.launch_persistent_context(
                    self.user_data_dir,
                    headless=self.headless,
                    slow_mo=500,
                    # Adding args to make it more robust in background
                    args=["--no-sandbox", "--disable-setuid-sandbox"] if self.headless else []
                )
            except Exception as e:
                print(f"CRITICAL: Failed to launch browser context: {e}", flush=True)
                # Fallback to non-persistent if persistent fails? 
                # No, we need the session.
                return False
            
            page = context.pages[0] if context.pages else await context.new_page()
            
            print(f"Navigating to {self.timesheet_url}...", flush=True)
            await page.goto(self.timesheet_url)
            
            await asyncio.sleep(5)
            
            is_login_page = any(pattern in page.url.lower() for pattern in ["login", "idp", "salesforce.com"])
            
            # Additional check: look for "Log in with Azure" button in any frame
            if not is_login_page:
                for frame in page.frames:
                    try:
                        if await frame.get_by_text("Log in with Azure").is_visible():
                            is_login_page = True
                            break
                    except:
                        continue

            if is_login_page:
                print(f"Login page detected. URL: {page.url}", flush=True)
                
                # Azure button search logic (Ported from PoC for robustness)
                azure_button_selectors = [
                    "text='Log in with Azure'",
                    "text='Login with Azure'",
                    "text='Azure'",
                    "button:has-text('Azure')",
                    "a:has-text('Azure')",
                    "button:has-text('Log in')",
                    ".sso-button",
                    "#idp_section_buttons button",
                    "id='azure_login_button'",
                ]
                
                button_found = False
                for frame in page.frames:
                    print(f"Searching for Azure button in frame: {frame.name or 'main'} ({frame.url[:50]}...)", flush=True)
                    
                    # Try Playwright's get_by_text
                    try:
                        azure_btn = frame.get_by_text("Log in with Azure", exact=True)
                        if await azure_btn.is_visible():
                            print(f"Found Azure button via get_by_text in frame: {frame.name or 'main'}", flush=True)
                            await azure_btn.click()
                            button_found = True
                            await self.handle_azure_login(page)
                            break
                    except:
                        pass
                    if button_found: break

                    # Try specific selectors
                    for selector in azure_button_selectors:
                        try:
                            button = await frame.query_selector(selector)
                            if button and await button.is_visible():
                                print(f"Found Azure button via selector: {selector} in frame: {frame.name or 'main'}", flush=True)
                                await button.click(force=True)
                                button_found = True
                                await self.handle_azure_login(page)
                                break
                        except:
                            continue
                    if button_found: break
                
                if not button_found:
                    if "microsoftonline.com" in page.url:
                        print("On Microsoft login page, attempting login flow...", flush=True)
                        await self.handle_azure_login(page)
                    else:
                        print("Azure login button not automatically found. Listing frame details...", flush=True)
                        for i, frame in enumerate(page.frames):
                            try:
                                print(f"  Frame {i}: {frame.name or 'main'} - {frame.url[:50]}...", flush=True)
                                # Quick content scan for 'azure' in any clickable element
                                suspects = await frame.query_selector_all("a, button")
                                for s in suspects:
                                    txt = await s.inner_text()
                                    if "azure" in txt.lower():
                                        print(f"    - Potential match: '{txt.strip()}' (Tag: {await s.evaluate('e => e.tagName')})", flush=True)
                            except:
                                continue
                        print("Waiting for manual login or redirect...", flush=True)
                
                try:
                    await page.wait_for_url("**/lightning/**", timeout=300000)
                except:
                    print("Timeout waiting for redirect to Lightning.", flush=True)
                    await context.close()
                    return False

            # Wait for timesheet component
            print("Waiting for timesheet component...", flush=True)
            await page.wait_for_selector(".oneCenterStage", timeout=30000)
            await asyncio.sleep(10) # Wait for iframes
            
            # Find the correct frame
            print("Scanning all frames for timesheet or login content...", flush=True)
            ts_frame = None
            for i, frame in enumerate(page.frames):
                frame_name = frame.name
                frame_id = await frame.evaluate("() => { try { return window.frameElement ? window.frameElement.id : ''; } catch(e) { return 'cross-origin'; } }")
                print(f"Frame {i}: Name='{frame_name}', ID='{frame_id}', URL='{frame.url[:80]}...'", flush=True)
                
                if "kimbleone" in frame.url.lower() or "visualforce" in frame.url.lower():
                    ts_frame = frame
                    print(f"Found likely timesheet frame at index {i}", flush=True)
                    break
            
            if not ts_frame:
                print("Could not find timesheet frame by URL. Checking content of all frames...", flush=True)
                for i, frame in enumerate(page.frames):
                    try:
                        content = await frame.content()
                        if "+ Time Entry" in content or "Kimble" in content:
                            ts_frame = frame
                            print(f"Found timesheet frame by content at index {i}", flush=True)
                            break
                    except:
                        continue
            
            if not ts_frame:
                print("CRITICAL: Could not find timesheet frame.", flush=True)
                try:
                    await page.screenshot(path="no_frame_found.png")
                    print("Screenshot saved as no_frame_found.png", flush=True)
                except:
                    pass
                await context.close()
                return False

            # --- Navigate to the correct week ---
            print(f"Ensuring we are on the week starting {week_start_date}...", flush=True)
            if not await self.navigate_to_week(page, week_start_date):
                print("Navigation failed - proceeding anyway, but might be on wrong week.", flush=True)

            # --- Target Frame Refinement for + Time Entry ---
            # Sometimes Kimble nests the ACTUAL grid in another iframe within the timesheet frame
            # The user says the correct iframe might look like 'vfFrameId_...'
            active_frame = ts_frame
            print("Checking all frames to find the best candidate for time entry operations...", flush=True)
            for frame in page.frames:
                frame_name = frame.name
                frame_id = await frame.evaluate("() => { try { return window.frameElement ? window.frameElement.id : ''; } catch(e) { return 'cross-origin'; } }")
                
                # Check for + Time Entry button existence in frame to identify active_frame
                try:
                    btns = await frame.query_selector_all("*[title='+ Time Entry']")
                    if len(btns) >= 7:
                        active_frame = frame
                        print(f"Targeting frame with 7+ '+ Time Entry' buttons: Name='{frame_name}', ID='{frame_id}'", flush=True)
                        break
                except:
                    continue

                # If no buttons found yet, try looking for the vfFrameId pattern user mentioned
                if "vfFrameId_" in (frame_name or "") or "vfFrameId_" in (frame_id or ""):
                    active_frame = frame
                    print(f"Targeting frame by user-provided pattern 'vfFrameId_': Name='{frame_name}', ID='{frame_id}'", flush=True)
                    # Don't break yet, finding buttons is a better indicator
            
            # Final fallback if still using top-level ts_frame but it has children that might be better
            if active_frame == ts_frame:
                for frame in page.frames:
                    if frame.parent_frame == ts_frame:
                        frame_name = frame.name
                        frame_id = await frame.evaluate("() => { try { return window.frameElement ? window.frameElement.id : ''; } catch(e) { return 'cross-origin'; } }")
                        print(f"Found child frame: Name='{frame_name}', ID='{frame_id}' - {frame.url[:80]}...", flush=True)
                        # If this child frame also looks like Kimble, it might be the real target
                        if "kimble" in frame.url.lower() or "visualforce" in frame.url.lower():
                            active_frame = frame
                            print("Targeting child frame for operations.", flush=True)
                            break

            # Ensure we have exactly 7 days of hours
            if len(day_hours) < 7:
                day_hours = list(day_hours) + [0] * (7 - len(day_hours))
            
            # The loop for day_idx starts here...
            for day_idx in range(7):
                # Skip Saturdays and Sundays (assuming 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun)
                if day_idx in [5, 6]:
                    print(f"Day {day_idx}: Skipping weekend.", flush=True)
                    continue
                
                current_day_hours = day_hours[day_idx]
                total_needed = 8.0
                non_working_needed = total_needed - current_day_hours
                
                print(f"Day {day_idx}: Working={current_day_hours}h, Non-Working={non_working_needed}h", flush=True)

                # We need to click "Add Time Entry" for this specific day
                # Retry loop for buttons to appear (might be slow loading)
                targets = []
                for retry in range(3):
                    targets = await active_frame.query_selector_all("*[title='+ Time Entry']")
                    if len(targets) >= 7:
                        break
                    # Try alternative selector if title fails
                    if len(targets) == 0:
                        targets = await active_frame.query_selector_all("button:has-text('+'), .plus-button, .btn-add-time")
                    
                    if len(targets) < 7:
                        print(f"  (Retry {retry+1}) Found {len(targets)} buttons, waiting...", flush=True)
                        await asyncio.sleep(3)
                
                visible_targets = []
                for t in targets:
                    if await t.is_visible():
                        visible_targets.append(t)
                
                if len(visible_targets) < 7:
                    print(f"Expected at least 7 visible '+ Time Entry' buttons, found {len(visible_targets)} in frame {active_frame.name or 'main'}", flush=True)
                    # If we found 0, let's log what we DID find for debugging
                    if len(visible_targets) == 0:
                        all_interactive = await active_frame.query_selector_all("button, a, span[onclick], .btn")
                        print(f"  Diagnostics: Listing first 10 clickable elements in frame:", flush=True)
                        for i, el in enumerate(all_interactive[:10]):
                            txt = (await el.inner_text()).strip()
                            ttl = await el.get_attribute("title")
                            print(f"    [{i}] text='{txt}', title='{ttl}'", flush=True)
                    continue
                
                # This is a bit fragile if there are multiple rows (multiple projects).
                # Assuming one project row for now as per POC.
                day_button = visible_targets[day_idx]
                
                # 1. Add Working Hours (if any)
                if current_day_hours > 0:
                    await self.add_entry(active_frame, day_button, current_day_hours, is_non_working=False, activity_type=activity_type)
                
                # 2. Add Non-Working Day Hours (if needed OR if 0 working hours)
                # Ensure where there are no hours for a day a non working time entry is added
                if non_working_needed > 0 or current_day_hours == 0:
                    # If current_day_hours is 0, non_working_needed will be 8.0
                    # So adding this explicit check just to satisfy the user requirement strictly.
                    await self.add_entry(active_frame, day_button, non_working_needed, is_non_working=True)
                
                if current_day_hours == 0 and non_working_needed == 0:
                    # Should not happen with 8h logic but just in case
                    pass

            print("Automation finished.", flush=True)
            await asyncio.sleep(5)
            await context.close()
            return True

    async def add_entry(self, frame, day_button, hours, is_non_working=False, activity_type=None):
        """Clicks add button and fills the dialog with specific Kimble selectors."""
        try:
            # Re-verify we have the right frame if it fails later
            target_frame = frame
            
            await day_button.scroll_into_view_if_needed()
            await day_button.click()
            await asyncio.sleep(4) # Increased wait for dialog to fully load
            
            # Use the specific names from user as primary candidates
            literal_user_selector = "input[name='j_id0:j_id1:j_id550:j_id588:j_id590:j_id647:entryUnits']"
            # Updated with exact selector from user for Non-Business Days
            non_working_literal = "input[name='j_id0:j_id1:j_id550:j_id588:j_id590:j_id705:j_id708'], input[name$=':j_id705:j_id708'], input[id$=':j_id705:j_id708']"
            
            units_selector = f"{literal_user_selector}, input[name$=':entryUnits'], input[id$=':entryUnits']"
            hours_selector = f"input[id*='TimeEntryValue'], input[name*='TimeEntryValue'], {non_working_literal}"
            
            # --- Activity Type ---
            # Either a specific engagement reference OR "Non-business Day"
            # User update: until the Activity has been selected no other fields appear on the modal
            activity_label = "Non-business Day" if is_non_working else activity_type
            
            if activity_label:
                # Scan all frames for the activity dropdown first, as it's the primary field that reveals others
                dropdown_selector = "select[id*='ActivityValue'], select[name*='Activity']"
                dropdown = await target_frame.query_selector(dropdown_selector)
                
                if not dropdown:
                    print(f"Activity dropdown not found in frame '{target_frame.name or 'unnamed'}'. Scanning all frames...", flush=True)
                    for f in target_frame.page.frames:
                        try:
                            check = await f.query_selector(dropdown_selector)
                            if check:
                                target_frame = f
                                dropdown = check
                                print(f"Found activity dropdown in frame: Name='{f.name or 'unnamed'}'", flush=True)
                                break
                        except:
                            continue

                if dropdown:
                    print(f"Selecting '{activity_label}' activity", flush=True)
                    # Try by label first, fallback to value if needed
                    try:
                        await dropdown.select_option(label=activity_label)
                    except:
                        # Fallback: maybe it's partially matched or needs a different approach
                        options = await dropdown.query_selector_all("option")
                        for opt in options:
                            txt = await opt.inner_text()
                            if activity_label.lower() in txt.lower():
                                await dropdown.select_option(value=await opt.get_attribute("value"))
                                break
                    
                    # IMPORTANT: After activity selection, other fields (dates, hours) should appear.
                    # Wait a bit for the modal to refresh/reveal fields.
                    await asyncio.sleep(2)
                else:
                    print(f"Warning: Could not find activity dropdown for '{activity_label}' in any frame", flush=True)

            # --- Date Fields ---
            # User wants to check/click the start and end dates
            # Selector from user: locator("input[name=\"j_id0:j_id1:j_id550:j_id588:j_id590:j_id601:entryStartDate\"]")
            # NOTE: User says clicking these fields opens a blocking calendar dialog that doesn't do anything.
            # Removing clicks as they were not working as intended.
            # start_date_selector = "input[name*='entryStartDate']"
            # end_date_selector = "input[name*='entryEndDate']"
            
            # start_date_input = await target_frame.query_selector(start_date_selector)
            # if start_date_input:
            #     print("Clicking Start Date field...", flush=True)
            #     await start_date_input.click()
            
            # end_date_input = await target_frame.query_selector(end_date_selector)
            # if end_date_input:
            #     print("Clicking End Date field...", flush=True)
            #     await end_date_input.click()

            # --- Hours (Units) Retry Loop ---
            # Re-locate the input field to ensure it's still there after activity selection (dialog might refresh)
            input_field = None
            for attempt in range(4): # Increased attempts as it might take time to reveal
                if is_non_working:
                    # For non-working time, try the non-working literal and entryUnits first
                    input_field = await target_frame.query_selector(non_working_literal) or \
                                 await target_frame.query_selector(units_selector) or \
                                 await target_frame.query_selector(hours_selector)
                else:
                    # For actual working time, user explicitly said the entry box is entryUnits.
                    input_field = await target_frame.query_selector(units_selector)
                    if not input_field:
                        print(f"Warning: entryUnits not found for working time (attempt {attempt+1}), trying fallback TimeEntryValue", flush=True)
                        input_field = await target_frame.query_selector(hours_selector)
                
                if input_field and await input_field.is_visible():
                    break
                
                print(f"Input field not found or not visible, retrying in 2s... (attempt {attempt+1})", flush=True)
                await asyncio.sleep(2)
                # Re-scan frames IF we still can't find it
                if not input_field:
                    for f in target_frame.page.frames:
                        try:
                            # Re-check all candidates in new frame
                            check = await f.query_selector(non_working_literal) or \
                                    await f.query_selector(units_selector) or \
                                    await f.query_selector(hours_selector)
                            
                            if check and await check.is_visible():
                                target_frame = f
                                input_field = check
                                print(f"Found input in different frame during retry: Name='{f.name or 'unnamed'}'", flush=True)
                                break
                        except:
                            continue

            if input_field:
                print(f"Filling {hours} hours...", flush=True)
                try:
                    await input_field.scroll_into_view_if_needed()
                    await input_field.fill("") # Clear first
                    await input_field.fill(str(hours))
                except Exception as fill_err:
                    print(f"Error filling input field: {fill_err}", flush=True)
            else:
                print(f"Warning: Could not find hours/units input field in frame '{target_frame.name or 'unnamed'}'", flush=True)
                # Diagnostics: List all inputs to help identify the correct one
                try:
                    all_inputs = await target_frame.query_selector_all("input")
                    print(f"  Diagnostics: Found {len(all_inputs)} total inputs in frame.", flush=True)
                    for i, inp in enumerate(all_inputs):
                        nm = await inp.get_attribute("name")
                        idd = await inp.get_attribute("id")
                        typ = await inp.get_attribute("type")
                        if nm or idd:
                            print(f"    Input[{i}]: name='{nm}', id='{idd}', type='{typ}'", flush=True)
                except:
                    pass
                
                # Take a screenshot for debugging if field is not found
                try:
                    await target_frame.page.screenshot(path="field_not_found.png")
                    print("Screenshot saved as field_not_found.png", flush=True)
                except Exception as screenshot_err:
                    print(f"Failed to save screenshot: {screenshot_err}", flush=True)
            
            # --- Save/Submit Button ---
            # Selector from user: get_by_role("button", name="Save")
            # User update: on the non-business day modal the save button is actually labelled "Submit For Approval"
            
            button_names = ["Save", "Submit For Approval"]
            button_found = False
            
            # Prioritize 'Submit For Approval' if non-working
            if is_non_working:
                button_names = ["Submit For Approval", "Save"]
            
            for btn_name in button_names:
                btn = target_frame.get_by_role("button", name=btn_name)
                if await btn.is_visible():
                    print(f"Clicking {btn_name} button", flush=True)
                    try:
                        await btn.click(force=True, timeout=5000)
                        button_found = True
                        break
                    except Exception as click_err:
                        print(f"{btn_name} button click failed/intercepted, trying fallback: {click_err}", flush=True)
                        await target_frame.dispatch_event(f"button:has-text('{btn_name}')", "click")
                        button_found = True
                        break
            
            if not button_found:
                # Fallback to other save/submit button selectors if get_by_role fails
                all_buttons_selector = "input[value='Save'], button:has-text('Save'), .btnSave, input[value='Submit For Approval'], button:has-text('Submit For Approval')"
                save_fallback = await target_frame.query_selector(all_buttons_selector)
                if save_fallback:
                    btn_text = await save_fallback.get_attribute("value") or await save_fallback.inner_text()
                    print(f"Clicking {btn_text.strip()} button (fallback selector)", flush=True)
                    await save_fallback.click(force=True)
                else:
                    print("Warning: Could not find Save or Submit For Approval button", flush=True)
            
            await asyncio.sleep(5) # Wait for dialog to close/process
        except Exception as e:
            print(f"Error adding entry: {e}", flush=True)

async def main():
    # Example usage
    auto = TimesheetAutomation(headless=False)
    # 8 hours for Mon-Fri, 0 for Sat-Sun
    # This will result in 8h working for M-F, and 8h non-working for Sat-Sun
    await auto.run_sync(datetime.now().date(), [8, 8, 8, 8, 8, 0, 0])

if __name__ == "__main__":
    asyncio.run(main())
