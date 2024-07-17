import json
import math
import time

from dotenv import load_dotenv

load_dotenv()  # take environment variables from .env.

import numpy as np
from playwright.sync_api import sync_playwright

from llm_responder.llm import llm

MY_NAME = "Jason Gauci"
MY_FIRST_NAME = "Jason"
QUESTIONS = [
    "Is the author of the message applying to work at Latitude?  Begin your answer with either \"yes\" or \"no\" followed by an explanation.",
    "Is the message asking the recipient to apply for a job at the author's company?  Begin your answer with either \"yes\" or \"no\" followed by an explanation.",
    "Is the message a sales pitch?  Begin your answer with either \"yes\" or \"no\" followed by an explanation.",
    f"Does the message ask if {MY_FIRST_NAME} is hiring other employees?  Begin your answer with either \"yes\" or \"no\" followed by an explanation.",
    "Is the message asking whether Latitude is hiring?  Begin your answer with either \"yes\" or \"no\" followed by an explanation.",
    "Is the message asking for a meeting or consulation?  Begin your answer with either \"yes\" or \"no\" followed by an explanation.",
    "Is the author of the message asking to share what their company does?  Begin your answer with either \"yes\" or \"no\" followed by an explanation.",
    "Is the message offering recruitment services?  Begin your answer with either \"yes\" or \"no\" followed by an explanation.",
    "Is the message offering software services?  Begin your answer with either \"yes\" or \"no\" followed by an explanation.",
    "Is the message a cold outreach?  Begin your answer with either \"yes\" or \"no\" followed by an explanation.",
    "Is the message about hiring development teams?  Begin your answer with either \"yes\" or \"no\" followed by an explanation.",
]
PRODUCT_NAME = "LLM_Autoresponder"

def random_sleep(approx_seconds:float=1.0):
    time.sleep(np.clip(np.random.normal(loc=1.5 * approx_seconds, scale=0.25 * approx_seconds, size=None), 1.0 * approx_seconds, 2.0 * approx_seconds))

def handle_login(page):
    print("Please log in using the window provided...")
    while True:
        print(page.context.cookies())
        time.sleep(1.0)
        cookies = page.context.cookies()
        print("***")
        for cookie in cookies:
            print(cookie["name"])
            if cookie["name"] == "li_at":
                print(json.dumps(cookies))
                with open("cookies.json", "w") as fp:
                    json.dump(cookies, fp)
                return True

def accept_friend_request(page):
    page.goto("https://www.linkedin.com/mynetwork/invitation-manager/")
    print(page.title())

    random_sleep(3)
    if page.get_by_role("heading", name="Sign In").count() > 0:
        handle_login(page)
        return True

    accept_buttons = page.get_by_role("button", name="Accept").all()

    got_friends = False

    for accept_button in accept_buttons:
        accept_button.click(force=True)
        got_friends = True
        random_sleep(3)
    
    return got_friends




def keep_message_unread(page):
    print("CLICKING")
    print(page.locator(".msg__detail").locator(".msg-thread-actions__control").count())
    page.locator(".msg__detail").locator(".msg-thread-actions__control").click(force=True)
    random_sleep()

    print("CLICKING")
    print(page.locator(".msg__detail").get_by_text("Unread").count())
    page.locator(".msg__detail").get_by_text("Unread").click(force=True)
    random_sleep()

def handle_unread_message(safe_people:set, page):
        page.goto("https://www.linkedin.com/messaging/?filter=unread")
        print(page.title())


        random_sleep(3)
        if page.get_by_role("heading", name="Sign In").count() > 0:
            handle_login(page)
            return True

        # Find all divs with class msg-conversation-card__content--selectable
        # For each, click it
        # Take the last p tag with class msg-s-event-listitem__body t-14 t-black--light t-normal
        try:
            page.wait_for_selector(".msg-conversation-card__content--selectable")
            random_sleep(3)
        except:
            print("NO UNREAD LEFT")
            return False
        conversations = page.locator(".msg-conversation-card__content--selectable")
        print(conversations)
        conversation_to_click = None
        person_in_conversation = None
        for conversation in conversations.all():
            print(conversation)
            person = conversation.get_by_role("heading").inner_text()
            print("PERSON", person)
            if person in safe_people:
                continue
            conversation_to_click = conversation
            person_in_conversation = person
            break
        if conversation_to_click is None:
            print("NO UNREAD LEFT")
            return False
        conversation_to_click.click(force=True)

        page.wait_for_selector(".msg-s-event-listitem__body")
        random_sleep()
        chat_messages = page.locator(".msg-s-event-listitem__body")
        print(chat_messages)
        all_chat_messages = chat_messages.all_inner_texts()
        print(all_chat_messages)

        skip = False

        person_name_in_messages = page.locator(".msg__detail").locator(".msg-s-message-group__name").all_inner_texts()
        for m in all_chat_messages:
            if PRODUCT_NAME in m:
                print("FOUND PRODUCT")
                print(m)
                skip = True

        if not skip:
            for m in person_name_in_messages:
                print(m)
                if MY_NAME in m:
                    print("FOUND MESSAGE FROM ME")
                    keep_message_unread(page)
                    skip = True
                    break

        if skip:
            # Already handled, so mark as safe to avoid sending a second auto response
            safe_people.add(person_in_conversation)
            return True

        auto_response = None
        all_chat_messages = ['\n\n'.join(all_chat_messages)]

        if True:
            for i, question in enumerate(QUESTIONS):
                if auto_response is not None:
                    break
                for message in all_chat_messages:
                    response = llm.llm(question,"Message: " + message, stop=[], echo=True)
                    if response.lower().startswith("yes"):
                        print("YES")
                        print(message)
                        print(response)
                        if i == 1:
                            # Keep the message unread if it's asking me to apply for a job instead of the other way around.
                            keep_message_unread(page)

                            print("NEED TO MARK AS SAFE")
                            print(f"{person_in_conversation} is safe")
                            safe_people.add(person_in_conversation)

                            return True
                        auto_response = response
                        break
                    elif response.lower().startswith("no"):
                        print("NO")
                        print(message)
                        print(response)
                    else:
                        print("OTHER")
                        print(message)
                        print(response)

        if auto_response is not None:
            auto_response = "Hello! This message has been muted by LLM_Autoresponder for this reason:\n\n" + auto_response + "\n\nIf you would like to work at Latitude AI or know someone who does, please visit our careers page: https://lat.ai/careers\n\nIf you actually know me personally, please contact me in another way, thanks!"
            page.locator(".msg-form__contenteditable").fill(auto_response)
            random_sleep()

            page.locator(".msg-form__send-button").click(force=True)
            random_sleep(60)

            print("CLICKING")
            print(page.locator(".msg__detail").locator(".msg-thread-actions__control").count())
            page.locator(".msg__detail").locator(".msg-thread-actions__control").click(force=True)
            random_sleep()

            if page.locator(".msg__detail").get_by_text("Unmute").count() > 0:
                # Already muted
                print("ALREADY MUTED")
            else:
                print("CLICKING")
                print(page.locator(".msg__detail").get_by_role("button").get_by_text("Mute").count())
                page.locator(".msg__detail").get_by_role("button").get_by_text("Mute").click(force=True)
                random_sleep()

                print("CLICKING")
                print(page.locator(".msg__detail").locator(".msg-thread-actions__control").count())
                page.locator(".msg__detail").locator(".msg-thread-actions__control").click(force=True)
                random_sleep()

            print("CLICKING")
            print(page.locator(".msg__detail").get_by_role("button").get_by_text("Other").count())
            other_element = page.locator(".msg__detail").get_by_role("button").get_by_text("Other")
            if other_element.count() > 0:
                other_element.click(force=True)
            random_sleep()

            #page.locator(".msg-thread-actions__dropdown-options")[3].click(force=True)
            #time.sleep(1.0)
        else:
            # Keep the message unread
            print("CLICKING")
            print(page.locator(".msg__detail").locator(".msg-thread-actions__control").count())
            page.locator(".msg__detail").locator(".msg-thread-actions__control").click(force=True)
            random_sleep()

            print("CLICKING")
            print(page.locator(".msg__detail").get_by_text("Unread").count())
            page.locator(".msg__detail").get_by_text("Unread").click(force=True)
            random_sleep()

            print("NEED TO MARK AS SAFE")
            print(f"{person_in_conversation} is safe")
            safe_people.add(person_in_conversation)


        # chat_text = ""
        # chat_text = h2t.handle(chat_text)

        return True

HEADLESS = False

def main():
    safe_people = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, slow_mo=50)
        context = browser.new_context()
        try:
            with open("cookies.json") as fp:
                cookies = json.load(fp)
        except FileNotFoundError:
            cookies = []
        context.add_cookies(cookies)
        page = context.new_page()
        try:
            a = 0
            # Accept any friend requests
            while accept_friend_request(page):
                a += 1
                if a == 10: return
                pass
            while handle_unread_message(safe_people, page):
                a += 1
                if a == 10: return
                pass
        except KeyboardInterrupt:
            print("Interrupted")
        finally:
            cookies = context.cookies()
            print(json.dumps(cookies))
            with open("cookies.json", "w") as fp:
                json.dump(cookies, fp)
            page.close()
            context.close()
            browser.close()


if __name__ == "__main__":
    main()

