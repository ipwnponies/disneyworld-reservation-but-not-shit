import enum
import itertools
import json
import smtplib
from collections import namedtuple
from email.mime.text import MIMEText
from textwrap import dedent
from typing import Dict
from typing import List
from typing import Tuple

import arrow
import bs4
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Firefox
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as expected
from selenium.webdriver.support.wait import WebDriverWait
from tabulate import tabulate

from disney_reservation.config import config

Data = namedtuple('Data', 'date meal time')


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

    return times


def print_output(lost_reservations, new_reservations):
    email_template = dedent('''Lost reservations
    {}

    New reservations
    {}
    ''')

    msg = email_template.format(
        tabulate([Data(*i) for i in lost_reservations], headers='keys'),
        tabulate([Data(*i) for i in new_reservations], headers='keys'),
    )

    if config.mail.enable and (lost_reservations or new_reservations):
        print('Emailing results')
        email_results(msg)
    else:
        print(msg)


def email_results(message):

    email_message = MIMEText(message)
    email_message['Subject'] = 'Reservations availability at Somewhere'
    email_message['From'] = config.mail.sender
    email_message['To'] = ','.join(config.mail.recipients)

    with smtplib.SMTP(config.mail.smtp_server) as server:
        server.starttls()
        server.login(config.mail.sender, config.mail.password)
        server.send_message(email_message)


def get_changes_from_last_run(results) -> Tuple[List[Data], List[Data]]:
    try:
        with open('availability.json', 'r') as file:
            old_results = [Data(*i) for i in json.load(file)]
    except FileNotFoundError:
        old_results = []

    with open('availability.json', 'w') as file:
        # Save new results
        json.dump(results, file)
    # Get difference
    lost_reservations = set(old_results) - set(results)
    new_reservations = set(results) - set(old_results)

    return lost_reservations, new_reservations


def scheduled_main(driver, wait, actions, dates, meals=Meal):
    results = []
    for date, meal in itertools.product(dates, meals):
        print(f'Starting for {date} {meal.name}')
        try:
            times = query_available_times(driver, wait, actions, date, meal)
            for i in times:
                results.append(Data(date.format('YYYY-MM-DD'), meal.name, i))
        except TimeoutException:
            print('Timed out, givin up...')
        driver.refresh()

    lost_reservations, new_reservations = get_changes_from_last_run(results)
    print_output(lost_reservations, new_reservations)


def main():
    options = Options()
    options.add_argument('--headless')
    with Firefox(executable_path='geckodriver', options=options) as driver:
        wait = WebDriverWait(driver, timeout=10)
        actions = ActionChains(driver)

        driver.set_window_size(1200, 600)
        # TODO: Read url from config
        driver.get('REPLACE_ME')

        dates = [
            arrow.get('2019-05-24'),
            arrow.get('2019-05-25'),
            arrow.get('2019-05-26'),
        ]

        scheduled_main(driver, wait, actions, dates, [Meal.dinner])
