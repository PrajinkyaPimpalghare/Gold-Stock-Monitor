"""============================================================================
INFORMATION ABOUT CODE         Coding: ISO 9001:2015
===============================================================================
Monitors Gold Stocks Prices From Differnt Regions Of The World. Provide Tool Popup
Alert as well mail alerts about major changes.
User Google Finance, Yahoo Finance and Alpha Advantage Website.
Author: Prajinkya Pimpalghare
Date: 29-August-2019
Version: 1.0
Input Variable: Config.txt  - With DEtails of Mail and Stocks to Monitor.
============================================================================"""
try:
    from Tkinter import *
    from ttk import *
except ImportError:  # Python 3
    from tkinter import *
    from tkinter import messagebox
    from tkinter.ttk import *
from retrying import retry
from yahoo_finance import Share
from bs4 import BeautifulSoup
from datetime import datetime
from threading import Thread
import smtplib
import time
import requests


class GetServerDetails(object):
    """
    For Handling Different API for Getting stock data every second and creating the alert
    """

    def __init__(self, api_key, stocks_list, smtp_username, smtp_password, sender, receiver):
        """
        Constructor which will handle all the basic operation of API's
        :param api_key: Alpha Advantage API key , for getting Gold price coverage over last 30 days.
        :param stocks_list: Stocks to be considered for Checking alert
        :param smtp_username: Mail server Username
        :param smtp_password: Mail server Password
        :param sender: From whom mail alert should be sent
        :param receiver: To whom mail alert should be sent
        """
        self.stock_server = "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={1}&interval=5min&outputsize=compact&apikey={0}"
        self.api_key = api_key
        self.stock_list = stocks_list
        self.receiver = receiver
        self.sender = sender
        self.dummy_value = "N/A"
        self.alert_data = {"GoldChange": None, "STOCKS": {}}
        self.analysis_data = ("", "")
        self.alert_frequency = {"NUGT": [0, ""], "DUST": [0, ""]}
        self.gold_data = {"RSI": None, "LATEST": 0}
        self.today_date = datetime.now().date()
        self.server = self.configure_mail_server(smtp_username, smtp_password)
        print("(OPEN,HIGH,LOW,CLOSE,LATEST,VOLUME,CHANGE)")
        self.display = None
        self.google_yahoo_switch = False
        Thread(target=self.get_gui).start()
        while True:  # Unlimited loop
            if self.analysis_data == ("", ""):  # For getting gold up and down, only once per day
                Thread(target=self.alpha_advantage_api, args=["GOLD"]).start()
                self.today_date = datetime.now().date()
            if self.today_date == datetime.now().date():
                self.today_date = datetime.now().date()
                Thread(target=self.alpha_advantage_api, args=["GOLD"]).start()
            Thread(target=self.query_search_gold).start()  # Getting Latest Gold Value
            Thread(target=self.query_gold_rsi).start()  # Getting Latest Gold RSI
            for stocks in stocks_list:
                self.get_stock_details(stocks)  # Getting Stock details for each stock
            time.sleep(1)
            try:
                self.display.update_extra_data(self.gold_data["RSI"], self.gold_data["LATEST"], self.analysis_data, str(
                    len(self.stock_list) + 2))  # Updating GOLD RSI and LATEST value in GUI
            except:
                pass

    @retry(stop_max_attempt_number=3)
    def get_stock_details(self, stock_name):
        """
        For getting Detail of each Stock using different API
        :param stock_name:
        """
        time.sleep(1)
        Thread(target=self.query_search_yahoo, args=[stock_name]).start()  # Getting details from Yahoo API
        # if self.google_yahoo_switch: #  If getting data from Yahoo fails ,get data from google API
        #    Thread(target=self.query_search_google, args=[stock_name]).start()

    def query_search_google(self, query):
        """
        Custom API for getting stocks data from google
        :param query:
        """
        soup = self.access_server("https://www.google.com/search?q={0} stocks&ie=utf-8&oe=utf-8".format(
            query))  # Checking the server is responding or not and getting its details
        if soup:
            open = self.execute('soup.find("b", text=re.compile("Open")).find_next("td").text', soup)
            high = self.execute('soup.find("b", text=re.compile("High")).findNext("td").text', soup)
            low = self.execute('soup.find("b", text=re.compile("Low")).findNext("td").text', soup)
            volume = self.execute('soup.find("b", text=re.compile("Volume")).findNext("td").text', soup)
            latest = self.execute('soup.find("b", text="{0}").findNext("b").text'.format(query.upper()), soup)
            change = self.execute('soup.find("b", text="{0}").parent.text.split("{0}")[-1].strip()'.format(latest),
                                  soup)
            close = self.execute(
                'soup.find("a", text=re.compile("Holdings")).findNext("a").findNext("a").findNext("a").text.split(":")[0].strip().split(" ")[-3]',
                soup)
            if change == self.dummy_value:
                self.alert_monitor(query, latest, change, volume)  # Checking Stock alert
            else:
                self.alert_monitor(query, latest, change.split("(")[-1].split("%)")[0], volume)  # Checking Stock alert
            self.google_yahoo_switch = False
            self.log(message_type="GOOGLE STOCKS " + query, values=[open, high, low, close, latest, volume, change])

    def query_search_yahoo(self, query):
        """
        Custom API for getting stocks data from yahoo
        :param query:
        """
        soup = self.access_server("https://finance.yahoo.com/quote/{0}/".format(
            query))  # Checking the server is responding or not and getting its details
        if soup:
            open = self.execute('soup.find("td", text=re.compile("Open")).find_next("td").text', soup)
            close = self.execute('soup.find("td", text=re.compile("Previous")).find_next("td").text', soup)
            volume = self.execute('soup.find("td", text=re.compile("Volume")).find_next("td").text', soup)
            high = self.execute('soup.find("td", text=re.compile("Day")).find_next("td").text.split("-")[1]', soup)
            low = self.execute('soup.find("td", text=re.compile("Day")).find_next("td").text.split("-")[0]', soup)
            latest = self.execute(
                'soup.find("span", text=re.compile(r"[+-|].*[.].*[ ][(]([+-]|)(.*)[.].*[%][)]")).findPrevious("span").text',
                soup)
            change = self.execute('soup.find("span", text=re.compile(r"[+-|].*[.].*[ ][(]([+-]|)(.*)[.].*[%][)]")).text',
                                  soup)
            if change == self.dummy_value:
                self.alert_monitor(query, latest, change, volume)  # Checking Stock alert
            else:
                self.alert_monitor(query, latest, change.split("(")[-1].split("%)")[0], volume)  # Checking Stock alert
            self.check_google_yahoo([open, high, low, close, latest, volume,
                                     change])  # Checking yahoo server is responding correct data or not
            self.log("YAHOO STOCKS " + query, [open, high, low, close, latest, volume, change])
        else:
            pass

    def query_search_gold(self):
        """
        Custom API for getting GOLD latest price and price Change
        """
        soup = self.access_server(
            "https://finance.yahoo.com/quote/xauusd=X?ltr=1")  # Checking server is responding or not and providing data
        if soup:
            latest = self.execute(
                'soup.find("span", text=re.compile(r"[+-].*[.].*[ ][(]([+-]|)(.*)[.].*[%][)]")).findPrevious("span").text',
                soup)
            change = self.execute('soup.find("span", text=re.compile(r"[+-].*[.].*[ ][(]([+-]|)(.*)[.].*[%][)]")).text',
                                  soup)
            self.alert_data["GoldChange"] = change.split("(")[-1].split("%)")[0]
            self.gold_data["LATEST"] = latest
            print("[GOLD STOCK : ]", latest, change, self.gold_data["RSI"], str(datetime.now()))
        else:
            self.alert_data["GoldChange"] = "0.00"

    def alpha_advantage_api(self, query, increase=1, decrease=1):
        """
        Using Alpha advantage API for checking GOLD price up and down in last 30 days
        :param query:
        :param increase:
        :param decrease:
        """
        time.sleep(1)
        try:
            data = requests.get(self.stock_server.format(self.api_key, query)).json()
            time.sleep(1)
            data = list(data["Time Series (Daily)"].values())[::-1]  # Getting 30 days of data
            latest = data[0]["4. close"]  # Getting Gold price close value for last day
            for each in data[1:]:
                if float(each["4. close"]) >= float(latest):
                    decrease += 1
                    latest = each["4. close"]
                else:
                    break
            latest = data[0]["4. close"]
            for each in data[1:]:
                if float(each["4. close"]) <= float(latest):
                    increase += 1
                    latest = each["4. close"]
                else:
                    break
            if increase > decrease:
                self.analysis_data = (increase, "UP")  # Storing the Up Data in dictionary
            else:
                self.analysis_data = (decrease, "DOWN")  # Storing the Down Data in dictionary
        except:
            pass

    def query_gold_rsi(self):
        """
        Custom API for getting Gold RSI
        """
        soup = self.access_server("http://www.stockta.com/cgi-bin/analysis.pl?symb=GOLD&mode=table&table=rsi")
        if soup:
            self.gold_data["RSI"] = self.execute('soup.findAll("td", text="RSI Analysis")[1].findNext("td").text', soup)

    def get_gui(self):
        """
        Function to call Display Class initialization, for getting GUI
        """
        root = Tk()
        root.title("Gold Stock Watch")
        self.display = StockDisplay(root)
        self.display.create_gui()
        root.mainloop()

    def alert_monitor(self, query, latest, change, volume):
        """
        This function will check is alert is raised or not, if yes send the alert and update the data
        :param query:
        :param latest:
        :param change:
        :param volume:
        """
        data = self.check_alert(query, latest, change, self.alert_data["GoldChange"],
                                volume)  # Checking alert can be raised or not
        if data[0]:
            self.send_alert(query, data[1], data[2])  # If alert is created send Alert mail and raise GUI pop up
        else:
            if query in self.alert_data["STOCKS"].keys():
                del self.alert_data["STOCKS"][query]

    def check_alert(self, stock_name, stock_value, change, gold_value, volume, alert=False):
        """
        Function to check alert on provided conditions and retrun back the alert flag
        :param stock_name:
        :param stock_value:
        :param change:
        :param gold_value:
        :param volume:
        :param alert:
        :return:
        """
        try:
            stock_multiple = round((float(change) / float(gold_value) * 100), 2)
            gold_multiple = float(gold_value)
            if not -0.1 <= gold_multiple <= 0.1:
                if -1.00 <= float(change) <= +1.00 and (stock_multiple >= 20 or stock_multiple <= -20):
                    alert = True
            if stock_name.upper() in ["NUGT", "DUST"]:
                self.display.update_data(stock_name, (
                    stock_value, str(stock_multiple) + "%", str(change) + "%", str(gold_multiple) + "%", volume, alert,
                    self.alert_frequency[stock_name.upper()][0], self.alert_frequency[stock_name.upper()][1]),
                                         self.stock_list.index(stock_name))  # Updating data in GUI
            else:
                self.display.update_data(stock_name, (
                stock_value, str(stock_multiple) + "%", str(change) + "%", str(gold_multiple) + "%", volume, alert),
                                         self.stock_list.index(stock_name))  # Updating DATA in GUI
            return [alert, stock_multiple, gold_multiple]
        except:
            if stock_name.upper() in ["NUGT", "DUST"]:
                self.display.update_data(stock_name, (stock_value, "N/A", str(change) + "%", "N/A", volume, alert,
                                                      self.alert_frequency[stock_name.upper()][0],
                                                      self.alert_frequency[stock_name.upper()][1]),
                                         self.stock_list.index(stock_name))  # Updating Data in GUI
            else:
                self.display.update_data(stock_name, (stock_value, "N/A", str(change) + "%", "N/A", volume, alert),
                                         self.stock_list.index(stock_name))  # Updating DATA in GUI
            return [alert, "N/A", "N/A"]

    def send_alert(self, stock_name, stock_multiple, gold_multiple):
        """
        If Alert flag is raised , send mail and Update pop up in GUI.
        :param stock_name:
        :param stock_multiple:
        :param gold_multiple:
        """
        if stock_name in self.alert_data["STOCKS"].keys():  # If Alert is already raised , skip the process
            pass
        else:
            self.alert_data["STOCKS"][stock_name] = None
            self.get_alert_frequency(stock_name)  # For updating Alert Frequency
            Thread(target=messagebox.showinfo,
                   args=("STOCK ALERT", "Check Stocks For [{0}]".format(stock_name))).start()  # Update GUI
            msg = "[ALERT : ] Please check the Stock {0} having Multiple({1}) and Gold({2})".format(stock_name,
                                                                                                    stock_multiple,
                                                                                                    gold_multiple)
            self.server.sendmail(self.sender, self.receiver, msg=msg)  # Send mail
            print("[ALERT : ] Please check the Stock {0} having Multiple({1}) and Gold({2})".format(stock_name,
                                                                                                    stock_multiple,
                                                                                                    gold_multiple))

    def get_alert_frequency(self, stock_name):
        """
        Checking How many times Alert has been raised / not back to back , as well updating the alert time
        :param stock_name:
        """
        if stock_name.upper() in ["NUGT", "DUST"]:
            self.alert_frequency[stock_name.upper()][0] += 1
            self.alert_frequency[stock_name.upper()][1] = datetime.now()

    def execute(self, command, soup=NONE):
        """
        Function for executing string command and handling error.
        :param command:
        :param soup:
        :return:
        """
        try:
            return eval(command)
        except:
            return self.dummy_value

    def check_google_yahoo(self, data, failed_count=0):
        """
        Cheking Yahoo server is working or not, if not setting flag for google to work
        :param data:
        :param failed_count:
        """
        for values in data:
            if values == self.dummy_value:
                failed_count += 1
        if failed_count > 3:
            self.google_yahoo_switch = True

    @staticmethod
    def log(message_type, values):
        """
        Just for printing custom messages
        :param message_type:
        :param values:
        """
        print_message = ""
        for data in values:
            print_message = print_message + data + " "
        print("[{0} :] {1}".format(message_type, print_message))

    @staticmethod
    def access_server(server_url):
        """
        For checking server is accessible or not , and returning the serve data
        :param server_url:
        :return:
        """
        try:
            data = requests.get(url=server_url).text
            soup = BeautifulSoup(data, "html.parser")
            return soup
        except BaseException as error:
            print("[NO ACCESS :] {0} Might have no internet access or wrong URL.Please check your connection".format(
                server_url))
            return NONE

    @staticmethod
    def configure_mail_server(smtp_username, smtp_password):
        """
        Configuring the mail server according to Data in Config.txt file
        :param smtp_username:
        :param smtp_password:
        :return:
        """
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(smtp_username, smtp_username, msg="Gold Stock Alert Configured , will revive the alerts")
            print("[SMTP SERVER SUCCESSFULLY CONFIGURED]")
            return server
        except:
            print("[SMTP SERVER FAILED]")
            return NONE


class StockDisplay(Frame, object):
    """
    Class for handling GUI related request and providing display
    """

    def __init__(self, parent, **kw):
        Frame.__init__(self, parent)
        super().__init__(**kw)
        self.tree_view = Treeview()
        self.tree_view['columns'] = (
            'LATEST VALUE', 'STOCK MULTIPLE', 'STOCK CHANGE', 'GOLD CHANGE', 'VOLUME', 'ALERT', "FREQUENCY", "SINCE")
        self.grid(sticky=(N, S, W, E))
        self.tree_view.tag_configure('alert', background='lightgreen')
        self.tree_view.tag_configure('skyblue', background='skyblue', font="Helvetica 12 bold")
        self.tree_view.tag_configure('extra', background='', font="Helvetica 12 bold")
        self.tree_view.tag_configure('noalert', background='')
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)

    def create_gui(self):
        """
        Creating base GUI using this function
        """
        self.tree_view.heading("#0", text='STOCK NAME')
        self.tree_view.column("#0", anchor='center', width=100)
        for elements in self.tree_view['columns']:
            self.tree_view.heading(elements, text=elements)
            self.tree_view.column(elements, anchor='center', width=100)
            self.tree_view.grid(sticky=(N, S, W, E))
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def update_data(self, stock_name, stock_value, column="1"):
        """
        Updating the stocks data in the GUI
        :param stock_name:
        :param stock_value:
        :param column:
        """
        stock_name = stock_name.strip("^").split(".TO")[0]
        if self.tree_view.exists(stock_name):
            try:
                for index, value in enumerate(stock_value):
                    self.tree_view.set(stock_name, index, str(value))
                if stock_value[-1]:
                    self.tree_view.item(stock_name, tags=("alert"))
                else:
                    if stock_name.upper() in ["NUGT", "DUST"]:
                        self.tree_view.item(stock_name, tags=("skyblue"))
                    else:
                        self.tree_view.item(stock_name, tags=("noalert"))
            except:
                print("[FAILED TO UPDATE :] {0} : VALUES : {1}".format(stock_name, stock_value))
        else:
            if stock_name.upper() in ["NUGT", "DUST"]:
                self.tree_view.insert('', '0', stock_name, text=stock_name, values=stock_value)
            else:
                self.tree_view.insert('', column, stock_name, text=stock_name, values=stock_value)
            if stock_value[-1]:
                self.tree_view.item(stock_name, tags=("alert"))
            else:
                if stock_name.upper() in ["NUGT", "DUST"]:
                    self.tree_view.item(stock_name, tags=("skyblue"))
                else:
                    self.tree_view.item(stock_name, tags=("noalert"))

    def update_extra_data(self, rsi, latest, trend, position):
        """
        Function for handling GOLD RSI data Display
        :param rsi:
        :param latest:
        :param trend:
        :param position:
        """
        values = (str(trend[1]) + " " + str(trend[0]) + " Days", "GOLD RSI:", str(rsi), "LATEST GOLD:", latest)
        if self.tree_view.exists("GOLD_DATA"):
            for index, value in enumerate(values):
                self.tree_view.set("GOLD_DATA", index, str(value))
        else:
            self.tree_view.insert('', position, "GOLD_DATA", text="TRENDS:", values=values)
            self.tree_view.item("GOLD_DATA", tags="extra")


if __name__ == '__main__':
    CONFIG_DATA = {}
    try:
        with open("Config.txt", "r") as file:
            data = file.readlines()
        for key in data:
            CONFIG_DATA[key.split("=")[0]] = key.split("=")[1]
        GetServerDetails(CONFIG_DATA["APIKEY"], CONFIG_DATA["STOCKS"].strip("\n").split(" "), CONFIG_DATA["SMTP_USERNAME"],
                         CONFIG_DATA["SMTP_PASSWORD"], CONFIG_DATA["SENDER"], CONFIG_DATA["RECEIVER"])
    except BaseException as error:
        print("[INPUT ERROR :] Please Check Config File : ", error)
