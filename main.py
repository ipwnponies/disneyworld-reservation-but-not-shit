import enum
import itertools
import smtplib
from email.mime.text import MIMEText
from typing import List, Dict

import arrow
import bs4
from apscheduler.schedulers.blocking import BlockingScheduler
from selenium.webdriver import Firefox
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as expected
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import TimeoutException
from tabulate import tabulate


@enum.unique
class Meal(enum.Enum):
    breakfast = 80000712
    lunch = 80000717
    dinner = 80000714


def parse_for_time(html_page) -> List[str]:
    soup = bs4.BeautifulSoup(html_page, 'html.parser')
    if soup.select_one('#timesContainer span.diningReservationInfoTitle.notAvailable'):
        return []

    time_elements = soup.select('#timesContainer .ctaAvailableTimesContainer .availableTime')

    return [i.get_text().strip() for i in time_elements]


def query_available_times(driver, wait, actions, date, meal) -> Dict:
    driver.get('https://disneyworld.disney.go.com/dining/magic-kingdom/be-our-guest-restaurant/')
    # Set date
    date_select_element = wait.until(
        expected.presence_of_element_located((By.ID, 'diningAvailabilityForm-searchDate')),
    )
    actions.move_to_element(date_select_element)
    date_select_element.send_keys(
        Keys.BACKSPACE*10 + date.format('MM/DD/YYYY'),
    )

    # Click dropdown to reveal choices
    meal_select_element = driver.find_element_by_css_selector('#searchTime-wrapper > div.select-toggle')
    actions.move_to_element(meal_select_element)
    meal_select_element.click()

    # Click choice
    meal_choice_element = driver.find_element_by_css_selector(
        f'#diningAvailabilityForm-searchTime-dropdown-list > li[data-value="{meal.value}"]',
    )

    driver.execute_script('arguments[0].click();', meal_choice_element)

    # Search for reals
    search_button = driver.find_element_by_id('dineAvailSearchButton')
    actions.move_to_element(search_button)
    search_button.click()

    # Wait until result is populated into this div
    wait.until(expected.visibility_of_element_located((By.CSS_SELECTOR, '#timesContainer span')))

    times = parse_for_time(driver.page_source)

    return {
        'date': date.format('YYYY-MM-DD'),
        'meal': meal.name,
        'times': times,
    }


def email_results(message):

    email_message = MIMEText(message)
    mail_config = {
        'subject': 'Reservations availability at Be Our Guest',
        'sender': 'example@example.com',
        'recipients': [
            'example@example.com',
        ],
    }
    email_message['Subject'] = mail_config['subject']
    email_message['From'] = mail_config['sender']
    email_message['To'] = ','.join(mail_config['recipients'])

    with smtplib.SMTP('example.com:587') as server:
        server.starttls()
        server.login(mail_config['sender'], 'i-am-a-passowrd')
        server.send_message(email_message)


def scheduled_main(driver, wait, actions):
    date = arrow.get('2019-05-24')
    dates = [
        arrow.get('2019-05-24'),
        arrow.get('2019-05-25'),
        arrow.get('2019-05-26'),
    ]

    results = []
    for date, meal in itertools.product(dates, Meal):
        print(f'Starting for {date} {meal.name}')
        try:
            times = query_available_times(driver, wait, actions, date, meal)
            if times['times']:
                results.append(times)
        except TimeoutException:
            print('Timed out, givin up...')
        driver.refresh()

    if False:
        print('Emailing results')
        email_results(tabulate(results, headers='keys'))
    else:
        print(tabulate(results, headers='keys'))


def main():
    options = Options()
    options.add_argument('--headless')
    with Firefox(executable_path='geckodriver', options=options) as driver:
        wait = WebDriverWait(driver, timeout=10)
        actions = ActionChains(driver)

        driver.set_window_size(1200, 600)
        driver.get('https://disneyworld.disney.go.com/dining/magic-kingdom/be-our-guest-restaurant/')

        scheduled_main(driver, wait, actions)

        # scheduler = BlockingScheduler()
        # scheduler.add_job(
        #     scheduled_main,
        #     trigger='cron',
        #     args=[
        #         driver,
        #         wait,
        #         actions,
        #     ],
        #     minute='*/5',
        # )
        # scheduler.start()


if __name__ == '__main__':
    main()
