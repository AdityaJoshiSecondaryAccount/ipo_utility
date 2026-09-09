from django.http.response import JsonResponse
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.models import Group, User
from django.contrib.auth import logout, authenticate, login
from .models import CurrentIpoName, GroupDetail, Order, OrderDetail, ClientDetail, CustomUser, RateList
from math import ceil
from django import forms
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.utils import timezone
from .filters import OrderFilter
import datetime
import uuid
from datetime import datetime
import csv
import io
import shutil
from zipfile import ZipFile
from io import BytesIO
from django.middleware import csrf
from django.utils import formats
from django.contrib.staticfiles.storage import staticfiles_storage
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle,Spacer, Paragraph
from reportlab.lib import colors
import os
from django.templatetags.static import static
import pandas as pd
from django.db.models import Avg, Max, Min, Sum,Exists, OuterRef
from django.db.models import Q
from django.db.models import F
from .decorators import allowed_users, Broker_only
from urllib.parse import unquote
import re,requests,json,base64 
from bs4 import BeautifulSoup
from requests.exceptions import ConnectTimeout,RequestException
from time import sleep
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from openpyxl import Workbook
import aiohttp
import asyncio
from asgiref.sync import sync_to_async,async_to_sync
from django.db.models.functions import Coalesce
from django.db import connection
import ssl
from django.utils.timezone import now,make_aware
from django.db import transaction
from django.core.paginator import Paginator
from django.views.generic import ListView
import traceback
from PIL import Image
from django.views.decorators.csrf import csrf_exempt
from io import StringIO
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import time
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import threading
from aiosmtplib import SMTP
from datetime import datetime,timedelta
from django.http.response import JsonResponse
from django.contrib.auth.models import Group, User
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from .models import CurrentIpoName, GroupDetail, Order, OrderDetail, ClientDetail, CustomUser, RateList,SharedLink
from django.http import JsonResponse
from telethon import TelegramClient
from .models import CustomUser
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from django.conf import settings
from urllib.parse import unquote_plus
from collections import defaultdict
import tempfile
from decimal import Decimal, ROUND_HALF_UP
from asgiref.sync import async_to_sync
from .models import CustomUser, CurrentIpoName, GroupDetail
from .models import Accounting, AccountingAuditLog, CurrentIpoName, GroupDetail
from django.db.models import Sum, Case, When, F, Value, DecimalField,FloatField , Q,Count
from django.shortcuts import render, get_object_or_404

from django.utils.html import escape, format_html

from io import BytesIO
import json
from django.utils.dateparse import parse_datetime
import decimal 
from  decimal import Decimal
# from django.db.models import Count
import imgkit
from django.template.loader import render_to_string
from django.urls import reverse
import urllib.parse
import aiosmtplib

def expiry_date_processor(request):
    if request.user.is_authenticated:
        try:
            user_profile = CustomUser.objects.get(username=request.user)
            expiry_date = user_profile.Expiry_Date
        except CustomUser.DoesNotExist:
            expiry_date = None
    else:
        expiry_date = None
    return {'expiry_date': expiry_date}

def isValidPAN(Z): 
    Result=re.compile("[A-Za-z]{5}\d{4}[A-Za-z]{1}") 
    return Result.match(Z) 

def format_remark(remark_json):
    """
    Format remark JSON into a human-readable string.
    Returns empty string if no remark exists.
    """
    if not remark_json:
        return ""
    
    parts = []
    
    # Add tags (from dropdown selections)
    if 'tags' in remark_json and remark_json['tags']:
        parts.append(', '.join(remark_json['tags']))
    
    # Add custom text
    if 'text' in remark_json and remark_json['text']:
        parts.append(remark_json['text'])
    
    return ' - '.join(parts) if parts else ""

def fetch_data_API(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
        data = response.json()
        return data
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"An error occurred: {req_err}")
    return None
# @allowed_users(allowed_roles=['Broker'])
@Broker_only
def index(request):
    if request.user.is_anonymous:
        return redirect("/login")
    products = CurrentIpoName.objects.filter(user=request.user).order_by('-id')
    # ratelist = []
    # for i in products:
    #     try:
    #         Ratelistitem = RateList.objects.get(
    #             user=request.user, RateListIPOName_id=i.id)
    #     except:
    #         Ratelistitem = 0
    #     ratelist.append(Ratelistitem)
    params = {'entry': products, 'product': products}
    return render(request, 'index.html', params)


@allowed_users(allowed_roles=['Customer'])
def indexforCustomer(request):
    if request.user.is_anonymous:
        return redirect("/login")
    products = CurrentIpoName.objects.filter(user=request.user.Broker_id)
    ratelist = []
    for i in products:
        try:
            Ratelistitem = RateList.objects.get(
                user=request.user.Broker_id, RateListIPOName_id=i.id)
        except:
            Ratelistitem = 0
        ratelist.append(Ratelistitem)
    params = {'entry': zip(products, ratelist), 'product': products}
    return render(request, 'index.html', params)

# <!--- Allotment Check Start

def linkin_function():
    def getDropDown(url):
        max_attempts=5
        timeout=10
        for attempt in range(1, max_attempts + 1):
            try:
                headers = {
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                }
                response = requests.post(url, headers=headers, verify='./pemfile/my_trust_store.pem',timeout=timeout)
                if response.status_code == 200:
                    json_data = response.json()
                    return json_data
                else:
                    return None
            except requests.RequestException as e:
                print(f"Attempt {attempt}: Error - {e}")
                sleep(0.5)
        return None

    url = 'https://in.mpms.mufg.com/Initial_Offer/IPO.aspx/GetDetails'
    json_data = getDropDown(url)

    if json_data:
        data = json_data
        soup = BeautifulSoup(f'''{data}''', "lxml")
        
        company_data_dict = {}
        for table in soup.find_all('table'):
            company_id = table.company_id.text
            company_name = table.companyname.text
            company_data_dict[company_name] = company_id
        normalized_dict = {
            re.sub(r'\s+', ' ', key.strip()): value
            for key, value in company_data_dict.items()
        }
        return normalized_dict

# def kefintech_function():
#     global dropdown_dict
#     def getDropDown(url ,max_attempts=5, timeout=10):
#         for attempt in range(1, max_attempts + 1):
#             try:
#                 response = requests.get(url, verify='./pemfile/kfintech.pem',timeout=timeout)
#                 if response.status_code == 200:
#                     return response.text
#                 else:
#                     return None
#             except RequestException as e:
#                 print(f"Attempt {attempt}: Error - {e}")
#                 sleep(0.5)
#         return None

#     urls = [
#         'https://kprism.kfintech.com/ipostatus/',#server3
#         'https://kosmic.kfintech.com/ipostatus/', #server1
#         'https://evault.kfintech.com/ipostatus/',#server2
#         'https://rti.kfintech.com/ipostatus/',#server5
#         'https://kcasop.kfintech.com/ipostatus/',#server4
#     ]
    
#     html_content = None
#     for url in urls:
#         html_content = getDropDown(url, max_attempts=5, timeout=10)
#         if html_content:
#             break

#     if html_content:
#         soup = BeautifulSoup(html_content, 'html.parser')
#         dropdown_options = soup.select('#ddl_ipo option')
#         data = [option.text for option in dropdown_options]
#         data2 = [option['value'] for option in dropdown_options]

#         dropdown_dict = dict(zip(data, data2))
#         normalized_dict = {
#             re.sub(r'\s+', ' ', key.strip()): value
#             for key, value in dropdown_dict.items()
#         }
#         return normalized_dict

def kefintech_function():
    global dropdown_dict
    
    response = requests.get('http://46.202.162.106:8000/api/IpoAllotment/get-karvy_dropdown')
    dropdown_dict = response.json()
    # print(dropdown_dict)
    return dropdown_dict
    
    # resp = requests.get(url, headers=headers, timeout=10, verify=False)
    # resp.raise_for_status()
    # soup = BeautifulSoup(resp.text, 'html.parser')

    # # find main.js script
    # script_tag = soup.find("script", src=re.compile(r"main\..*\.js$"))
    # if not script_tag:
    #     return None
    
    # js_url = url + script_tag["src"]
    # js_resp = requests.get(js_url, headers=headers, timeout=10)
    # js_resp.raise_for_status()

    # # extract JSON.parse('[...]')
    # match = re.search(r"JSON\.parse\('(\[.*?\])'\)", js_resp.text)
    # if not match:
    #     return None

    # json_str = match.group(1).encode().decode("unicode_escape")
    # data_list = json.loads(json_str)

    # build dropdown dict
    # dropdown_dict = {item["name"]: item["clientId"] for item in data_list}

    # return dropdown_dict
    
    # response = requests.get(url)
    # ipos = response.json()   # this is already a list of dicts
    # dropdown_dict = {ipo["UNIT_NAME"]: ipo["UCDBPRE"] for ipo in ipos}
    # print(dropdown_dict)
    # return dropdown_dict

def BigShareDropDown():
    global dropdown_dict
    def getDropDown(url):
        try:
            response = requests.get(url, verify=True)
            if response.status_code == 200:
                return response.text
            else:
                return None
        except requests.RequestException as e:
            print(f"Error: {e}")
            return None

    url = 'https://ipo.bigshareonline.com/IPO_Status.html'
    html_content = getDropDown(url)

    if html_content:
        soup = BeautifulSoup(html_content, 'html.parser')
        dropdown_options = soup.select('#ddlCompany option')
        data = [option.text for option in dropdown_options]
        data2 = [option.get('value', '') for option in dropdown_options]

        dropdown_dict = dict(zip(data, data2))
        normalized_dict = {
            re.sub(r'\s+', ' ', key.strip()): value
            for key, value in dropdown_dict.items()
        }
        return normalized_dict

def PurvaDropDown():
    global dropdown_dict
    def getDropDown(url):
        try:
            response = requests.get(url, verify=True)
            if response.status_code == 200:
                return response.text
            else:
                return None
        except requests.RequestException as e:
            print(f"Error: {e}")
            return None

    url = 'https://www.purvashare.com/investor-service/ipo-query'
    html_content = getDropDown(url)

    if html_content:
        soup = BeautifulSoup(html_content, 'html.parser')
        dropdown_options = soup.select('#company_id option')
        data = [option.text.strip() for option in dropdown_options]
        data2 = [option.get('value', '') for option in dropdown_options]

        dropdown_dict = dict(zip(data, data2))
        normalized_dict = {
            re.sub(r'\s+', ' ', key.strip()): value
            for key, value in dropdown_dict.items()
        }
        return normalized_dict

def SkyLineDropDown():
    global dropdown_dict
    def getDropDown(url):
        try:
            response = requests.get(url, verify=False)
            if response.status_code == 200:
                return response.text
            else:
                return None
        except requests.RequestException as e:
            print(f"Error: {e}")
            return None

    url = 'https://www.skylinerta.com/ipo.php'
    html_content = getDropDown(url)
    if html_content:
        soup = BeautifulSoup(html_content, 'html.parser')
        dropdown_options = soup.select('#company option')
        data = [option.text.strip() for option in dropdown_options[1:]]
        data2 = [option.get('value', '') for option in dropdown_options[1:]]
        dropdown_dict = dict(zip(data, data2))
        normalized_dict = {
            re.sub(r'\s+', ' ', key.strip()): value
            for key, value in dropdown_dict.items()
        }
        return normalized_dict

def IntegratedDropDown():
    global dropdown_dict
    def getDropDown(url):
        try:
            data = {'Req': 1,'Comp':'IPO'}
            response = requests.post(url,data= data,verify='pemfile/integrated.pem')
            if response.status_code == 200:
                return response.text
            else:
                return None
        except requests.RequestException as e:
            print(f"Error: {e}")
            return None

    url = 'https://www.integratedregistry.in/IRMS_V2/RegistrarsToAjax.aspx'
    html_content = getDropDown(url)
    if html_content:
        soup = BeautifulSoup(html_content, 'html.parser')
        dropdown_dict = {}

        for option in soup.find_all('option'):
            if option['value'] != '0':  # Skip the --select-- option
                dropdown_dict[option.text.strip()] = option['value']
        normalized_dict = {
            re.sub(r'\s+', ' ', key.strip()): value
            for key, value in dropdown_dict.items()
        }
        return normalized_dict

def MaashitlaDropDown():
    global dropdown_dict
    def getDropDown(url):
        try:
            response = requests.get(url, verify=False)
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except requests.RequestException as e:
            print(f"Error: {e}")
            return None

    url = 'https://api.maashitla.com/api/public-issue/companies'
    html_content = getDropDown(url)

    if html_content:
        soup = html_content
        data = [item['company_name'] for item in soup]
        data2 = [item['company_id'] for item in soup]
        dropdown_dict = dict(zip(data, data2))
        normalized_dict = {
            re.sub(r'\s+', ' ', key.strip()): value
            for key, value in dropdown_dict.items()
        }
        return normalized_dict
    
def CambridgeDropDown():
    global dropdown_dict
    def getDropDown(url):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response.text
            else:
                return None
        except requests.RequestException as e:
            print(f"Error: {e}")
            return None

    url = 'https://ipostatus1.cameoindia.com/'
    html_content = getDropDown(url)

    if html_content:
        soup = BeautifulSoup(html_content, 'html.parser')
        dropdown_options = soup.select('#drpCompany option')
        data = [option.text.strip() for option in dropdown_options[1:]]
        data2 = [option.get('value', '') for option in dropdown_options[1:]]

        dropdown_dict = dict(zip(data, data2))
        normalized_dict = {
            re.sub(r'\s+', ' ', key.strip()): value
            for key, value in dropdown_dict.items()
        }
        return normalized_dict

def MasDropDown():
    global dropdown_dict
    try:
        response = requests.get('https://www.masserv.com/opt.asp', timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            options = {}
            for a in soup.find_all('a', href=lambda x: x and 'asearch' in x):
                text_node = a.find_previous(string=re.compile('ALLOTMENT', re.I))
                if text_node:
                    name = text_node.strip()
                    name = re.sub(r'(?i)^IPO\s*-\s*', '', name)
                    name = re.sub(r'(?i)\s*ALLOTMENT STATUS.*', '', name).strip()
                    href = a.get('href').strip()
                    post_url = href.replace("asearch", "search1") 
                    options[name] = post_url
            dropdown_dict = options
            return options
    except Exception as e:
        print(f"Error fetching Mas Services dropdown: {e}")
    return {}

def MudraRTADropDown():
    try:
        # The populated dropdown is located on ipo.php
        response = requests.get('https://mudrarta.com/ipo.php', timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            select = soup.find('select', id='company')
            options = {}
            if select:
                for option in select.find_all('option'):
                    val = option.get('value')
                    text = option.text.strip()
                    if val and text not in ["Select Company", ""]:
                        # Clean up text if it has extra spaces
                        clean_name = " ".join(text.split())
                        options[clean_name] = val
            return options
    except Exception as e:
        print(f"Error fetching MudraRTA dropdown: {e}")
    return {}

def get_iponame_Dropdown(ipo_register_value):
    if ipo_register_value == 'Linkin':
        linkin_company_data = linkin_function()
        register_options = {
            "Linkin": remove_specific_options(list(linkin_company_data.keys()),unwanted_phrases) if linkin_company_data else [],  
        }
        return register_options
    
    if ipo_register_value == 'Kfintech':
        kefintech_company_data = kefintech_function()
        register_options = {
            "Kfintech": remove_specific_options(list(kefintech_company_data.keys()),unwanted_phrases) if kefintech_company_data else [],
        }
        return register_options
    
    if ipo_register_value == 'BigShare':
        BigShare_company_data = BigShareDropDown()
        register_options = {
            "BigShare": remove_specific_options(list(BigShare_company_data.keys()),unwanted_phrases) if BigShare_company_data else [],
        }
        return register_options
    
    if ipo_register_value == 'Purva':
        Purva_company_data = PurvaDropDown()
        register_options = {
            "Purva": remove_specific_options(list(Purva_company_data.keys()),unwanted_phrases) if Purva_company_data else [],
        }
        return register_options
    
    if ipo_register_value == 'SkyLine':
        Skyline_company_data = SkyLineDropDown()
        register_options = {
            "SkyLine":remove_specific_options(list(Skyline_company_data.keys()),unwanted_phrases) if Skyline_company_data else [],
        }
        return register_options
    
    if ipo_register_value == 'Integrated':
        Integrated_company_data = IntegratedDropDown()
        register_options = {
            "Integrated":remove_specific_options(list(Integrated_company_data.keys()),unwanted_phrases) if Integrated_company_data else [],
        }
        return register_options

    if ipo_register_value == 'Maashitla':
        Maashitla_company_data = MaashitlaDropDown()
        register_options = {
            "Maashitla":remove_specific_options(list(Maashitla_company_data.keys()),unwanted_phrases) if Maashitla_company_data else [],
        }
        return register_options
    
    if ipo_register_value == 'Cambridge':
        Cambridge_company_data = CambridgeDropDown()
        register_options = {
            "Cambridge":remove_specific_options(list(Cambridge_company_data.keys()),unwanted_phrases) if Cambridge_company_data else [],
        }
        return register_options

    if ipo_register_value == 'Mas':
        Mas_company_data = MasDropDown()
        register_options = {
            "Mas": remove_specific_options(list(Mas_company_data.keys()), unwanted_phrases) if Mas_company_data else [],
        }
        return register_options

    if ipo_register_value == 'MudraRTA':
        MudraRTA_company_data = MudraRTADropDown()
        register_options = {
            "MudraRTA": remove_specific_options(list(MudraRTA_company_data.keys()), unwanted_phrases) if MudraRTA_company_data else [],
        }
        return register_options

unwanted_phrases = {"Select Company", "--Select--", "--Select Company--", "Select Company"}

def remove_specific_options(company_list, unwanted_phrases):
    # Remove the first item if it matches any of the unwanted phrases
    if company_list and company_list[0] in unwanted_phrases:
        return company_list[1:]  # Skip the first item
    return company_list

def encVal(vl):
    key = b'8080808080808080'
    iv = b'8080808080808080'

    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_data = pad(vl.encode(), AES.block_size)
    encrypted_data = cipher.encrypt(padded_data)
    
    return base64.b64encode(encrypted_data)

def get_options(request):
    PRI_limit  = CustomUser.objects.get(username = request.user)
    is_premium_user = PRI_limit.Allotment_access    
    
    if str(is_premium_user) == 'True':
        ipo_register_value = request.GET.get('ipo_register')
        DropDown = get_iponame_Dropdown(ipo_register_value)
        options = DropDown.get(ipo_register_value, [])
        return JsonResponse(options, safe=False)
    else:
        return None

# @sync_to_async
# def bulk_create_or_update(entries):
#     # with transaction.atomic():
#         # Separate entries into those that need to be created and those that need to be updated
#     objects_to_update = []

#     for entry in entries:
#         # Check if the record exists
#         existing_entry = OrderDetail.objects.get(
#             user=entry['user'],
#             Order__OrderIPOName_id=entry['IPOid'],
#             OrderDetailPANNo__PANNo=entry['panno'],
#             Order__OrderType=entry['OrderType'],
#         )
#         if existing_entry:
#             # If the record exists, update it
#             existing_entry.AllotedQty = int(entry['shares_alloted'])
#             objects_to_update.append(existing_entry)

#     if objects_to_update:
#         OrderDetail.objects.bulk_update(objects_to_update, fields=['AllotedQty'])


# @sync_to_async
# def update_database(user, IPOid, panno, shares_alloted,OrderType):
#     entry = OrderDetail.objects.get(user=user, Order__OrderIPOName_id=IPOid, OrderDetailPANNo__PANNo=panno,Order__OrderType=OrderType)
#     entry.AllotedQty = int(shares_alloted)
#     entry.save()


async def update_database(user, IPOid, panno, shares_alloted, OrderType):
    try:
        entry = await sync_to_async(OrderDetail.objects.get)(
            user=user,
            Order__OrderIPOName_id=IPOid,
            OrderDetailPANNo__PANNo=panno,
            Order__OrderType=OrderType
        )
        entry.AllotedQty = int(shares_alloted)
        await sync_to_async(entry.save)()
    except Exception as e:
        print(f"Error updating database: {e}")

async def linkin_token(session, url,ssl_context,retries=3, timeout=5):
    # ssl_context = ssl.create_default_context(cafile='pemfile/my_trust_store.pem')
    for attempt in range(retries):
        try:
            async with session.post(url ,ssl = ssl_context) as response:
                json_data = await asyncio.wait_for(response.text(), timeout)
                data = json.loads(json_data)
                number = data["d"]
                response = number 
                encrypted_value = encVal(response)
                token = encrypted_value.decode()
                return token
            
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            print(f"Retrying... (Attempt {attempt + 1}/{retries})")
            attempt = attempt + 1
        
        except:
            if attempt < retries:
                attempt = attempt + 1
            

async def Linkin_fetch_allotment(user,session, selected_key, panno, result,IPOid,OrderType,ssl_context,retries=3, timeout=5):
    
    # def update_database(user, IPOid, panno, shares_alloted,OrderType):
    #     entry = OrderDetail.objects.get(user=user, Order__OrderIPOName_id=IPOid, OrderDetailPANNo__PANNo=panno,Order__OrderType=OrderType)
    #     entry.AllotedQty = int(shares_alloted)
    #     entry.save()
    
    tknurl = 'https://in.mpms.mufg.com/Initial_Offer/IPO.aspx/generateToken'
    
    token = await linkin_token(session, tknurl,ssl_context)
    myobj = {'clientid': selected_key, 'PAN': panno, 'IFSC': '', 'CHKVAL': '1','token': token}
    
    url = "https://in.mpms.mufg.com/Initial_Offer/IPO.aspx/SearchOnPan"
    # ssl_context = ssl.create_default_context(cafile='pemfile/my_trust_store.pem')
    for attempt in range(retries):
        flag = 0
        try:
            async with session.post(url,data = json.dumps(myobj),ssl = ssl_context) as response:
                soup = await response.json()
                soup = BeautifulSoup(f'''{soup}''', "lxml")
                
                if not soup.find('newdataset').contents:
                    result['QTY1'] = 'No Record Found'
                    result['REMRAK'] = 'DONE'
            
                try:
                    msg = soup.msg
                    msg1 = msg.text
                except:
                    msg1 = None
                
                if msg1 is not None:
                    result['QTY1'] = msg1
                    
                dpclitid = []    
                try:
                    dpclitid = [table.dpclitid for table in soup.find_all('table')]
                except:
                    dpclitid.append(None)
                    
                for j, dpclitid1 in enumerate(dpclitid):
                    if dpclitid1 is not None:
                        dpclitid1= dpclitid1.text
                    result[f'DpID-ClientID{j+1}'] = dpclitid1

                invcode_list = []
                try:
                    invcode_list = [table.invcode for table in soup.find_all('table')]
                except:
                    invcode_list.append(None)

                bankcode_list = [] 
                try:
                    bankcode_list = [table.bnkcode for table in soup.find_all('table')]
                except:
                    bankcode_list.append(None)
                
                for j, invcode1 in enumerate(invcode_list):
                    if invcode1 is not None:
                        invcode1 = invcode1.text
                    if bankcode_list[j] is not None:
                        bankcode = bankcode_list[j].text
                        
                    if invcode1 == '91' and bankcode == '0':
                        flag = 1
                        result[f'QTY{j+1}'] = 'Application bidded but amount not blocked'
                    
                offer_price = []    
                try:
                    offer_price = [table.offer_price for table in soup.find_all('table')]
                except:
                    offer_price.append(None)
                    
                for j, offer_price1 in enumerate(offer_price):
                    if offer_price1 is not None:
                        offer_price1 = offer_price1.text
                    result[f'Cut Off Price{j+1}'] = offer_price1
            
                allot = []    
                try:
                    allot = [table.allot for table in soup.find_all('table')]
                except:
                    allot.append(None)

                Name = []    
                try:
                    Name = [table.name1 for table in soup.find_all('table')]
                except:
                    Name.append(None)
                
                for j, Name1 in enumerate(Name):
                    if Name1 is not None:
                        Name1 = Name1.text
                    result[f'Name{j+1}'] = Name1
                
                if Name and all(item is None for item in Name):
                    flag = 1
                    
                allotqty  =  0
                for i, (j, allot1) in enumerate(zip(range(len(allot)), allot)):
                    if allot1 is not None:
                        allot1 = allot1.text
                        allotqty = int(allot1) + allotqty
                        if flag == 0:
                            if int(allotqty) >= 0:
                                try :
                                    await update_database(user, IPOid, panno, allotqty ,OrderType)
                                except Exception as e:
                                    print(e)
                
                            result[f'QTY{j+1}'] = allot1
            
                pemndg = []    
                try:
                    pemndg = [table.pemndg for table in soup.find_all('table')]
                except:
                    pemndg.append(None)
                
                for j, pemndg1 in enumerate(pemndg):
                    if pemndg1 is not None:
                        pemndg1 = pemndg1.text
                    result[f'Category{j+1}'] = pemndg1
                
                result['REMRAK'] = 'DONE'
                return result
        
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            print(f"ConnectionError for PAN {panno}. Retrying... (Attempt {attempt + 1}/{retries})")

        except Exception as e:
            result['REMRAK'] = e
            return result

async def linkin_allotment(user,IPOid,OrderType,ipo_register,ipo_name,Data):
    
    entry = Data
    data_length = len(entry)
    
    def get_key_by_value(dictionary, value):
        for key, val in dictionary.items():
            if key == value:
                return val
    
    selected_text = ipo_name
    linkin_company_data = linkin_function()
    IPO_Name_dic = linkin_company_data
    
    selected_key = get_key_by_value(IPO_Name_dic, selected_text)
        
    results = []
    
    ssl_context = ssl.create_default_context(cafile='pemfile/my_trust_store.pem')
    async with aiohttp.ClientSession(headers={
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Content-Type': 'application/json; charset=UTF-8',
        'Cookie': '_ga=GA1.1.897427883.1703307036; _ga_T3ER3Y8R0E=GS1.1.1705735885.6.1.1705736037.0.0.0',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }) as session:
        tasks = []
        for i in range(data_length):
            panno = entry[i]
            result = {'PAN': panno}
            tasks.append(Linkin_fetch_allotment(user,session, selected_key, panno, result,IPOid,OrderType,ssl_context))

        responses = await asyncio.gather(*tasks)
        # updates = []
        # for res in responses:
        #     if 'QTY1' in res:
        #         if res['QTY1'] != 'No Record Found' and res['Name1'] != '' and res['QTY1'] != 'Application bidded but amount not blocked' and res['QTY1'].isdigit() and int(res['QTY1']) >= 0 : 
        #             qty_sum = 0
        #             for key, value in res.items():
        #                 if key.startswith('QTY'):  # Check if the key starts with 'QTY'
        #                     qty_sum += int(value)
                            
        #             if 'QTY1' in res:
        #                 updates.append({
        #                     'user': user,
        #                     'IPOid': IPOid,
        #                     'panno': res['PAN'],
        #                     'shares_alloted': qty_sum,
        #                     'OrderType': OrderType,
        #                 })
        
        # await bulk_create_or_update(updates)
        results.extend(responses)

    df = pd.DataFrame(results)
    IPO_name = ipo_name
    IPO_NAME = IPO_name.split()
    ipon = IPO_NAME[0]

    # Write to Excel using pandas
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{ipon}_{IPO_NAME[1]}_IPO_Allotment.xlsx"'
    
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='IPO Allotment')
    
    return response

async def Kfintech_fetch_allotment(user, headers, panno,ssl_context, result,IPOid,OrderType,retries=3, timeout=5):
    url = 'https://0uz601ms56.execute-api.ap-south-1.amazonaws.com/prod/api/query?type=pan'
    for attempt in range(retries):
        flag = 0
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url) as response:
                    
                    soup = await response.json()
                    if 'data' in soup:
                        alloti_Qty = 0
                        for j,entry in enumerate(soup['data']):
                            appl_no = entry['Appln_No']
                            name = entry['Name']
                            if name == '' or name == '.':
                                flag = 1
                            applied = entry['App_Shares']
                            alloti = entry['All_Shares']
                            if alloti is not None:
                                if flag == 0:
                                    if int(alloti) >= 0:
                                        alloti_Qty = alloti_Qty + int(alloti)
                                        try :
                                            await update_database(user, IPOid, panno,alloti_Qty ,OrderType)
                                        except Exception as e:
                                            print(e)
                                            pass
                                
                            # msg = entry['MSG']
                            DP_CLID = entry['DP_CLID']    
                            # ipo_status = entry['IPO_STATUS']    
                            result[f'Appl.No{j+1}'] = appl_no
                            result[f'Name{j+1}'] = name
                            result[f'Applied{j+1}'] = applied
                            result[f'QTY{j+1}'] = alloti
                            # if alloti is None:
                            result[f'DPID{j+1}'] = DP_CLID
                            # result[f'IPO_STATUS{j+1}'] = ipo_status
                        result['REMRAK'] = 'DONE'
                        return result
                    else:
                        result['REMRAK'] = 'DONE'
                        result[f'QTY1'] = soup['error']
                        return result
        
        except aiohttp.ClientConnectionError:
            print(f"ConnectionError for PAN {panno}. Retrying... (Attempt {attempt + 1}/{retries})")
        
        except Exception as e:
            traceback.print_exc()
            result['REMRAK'] = 'ERROR'
            return result

async def Kfintech_allotment(user,IPOid,OrderType,ipo_register,ipo_name,Data):
    entry = Data
    ssl_context = ssl.create_default_context(cafile=r'pemfile/kfintech.pem')
    
    data_length = len(entry)
    
    kefintech_company_data = kefintech_function()
    IPO_options_dict = kefintech_company_data
    selected_text = ipo_name
    selected_value = IPO_options_dict.get(selected_text, "")
    
    results = []
    
    # async with aiohttp.ClientSession(headers={
    #     'Accept-Language': 'en-US,en;q=0.9',
    #     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    #     'X-Requested-With': 'XMLHttpRequest' 
    # }) as session:
    tasks = []
    for i in range(data_length):
        panno = entry[i]
        # myobj = {
        #     'ipodets': selected_value,
        #     'queryby': 'P',
        #     'qval': panno,
        # }
        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'client_id': selected_value,
            'reqparam': panno,
        }
        result = {'PAN': panno}
        tasks.append(Kfintech_fetch_allotment(user,headers, panno,ssl_context, result,IPOid,OrderType))

    responses = await asyncio.gather(*tasks)
    
    results.extend(responses)

    df = pd.DataFrame(results)
    IPO_name = ipo_name
    IPO_NAME = IPO_name.split()
    ipon = IPO_NAME[0]

    # Write to Excel using pandas
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{ipon}_{IPO_NAME[1]}_IPO_Allotment.xlsx"'
    
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='IPO Allotment')
    
    return response        

async def BigShare_fetch_allotment(session,user, myobj, panno, result,IPOid,OrderType,ssl_context,retries=3, timeout=5):
    url = 'https://ipo.bigshareonline.com/Data.aspx/FetchIpodetails'
    # ssl_context = ssl.create_default_context(cafile=r'pemfile/_.bigshareonline.pem')
    for attempt in range(retries):
        try:
            async with session.post(url, data=json.dumps(myobj),ssl = ssl_context) as response:
                soup = await response.json()
                soup = BeautifulSoup(f'''{soup}''', "lxml")
                tag21 = soup.find('p').text
                try:
                    dpid_data = eval(tag21)['d']['DPID']
                    result['DPID'] = dpid_data
                except (AttributeError, KeyError):
                    result['DPID'] = None
                    
                try:
                    App_no = eval(tag21)['d']['APPLICATION_NO']
                    result['APPLICATION_NO'] = App_no
                except (AttributeError, KeyError):
                    result['APPLICATION_NO'] = None
                    
                try:
                    Name = eval(tag21)['d']['Name']
                    result['Name'] = Name
                except (AttributeError, KeyError):
                    result['Name'] = None
                
                try:
                    Applied = eval(tag21)['d']['APPLIED']
                    result['APPLIED'] = Applied
                except (AttributeError, KeyError):
                    result['APPLIED'] = None
                    
                try:
                    alloted1 = eval(tag21)['d']['ALLOTED']
                    if alloted1 == "NON-ALLOTTE":
                        alloted1 = 0
                    result['QTY'] = alloted1
                    if alloted1 != '':
                        if Name != '':
                            if int(alloted1) >= 0:
                                await update_database(user, IPOid, panno,alloted1 ,OrderType)
                except (AttributeError, KeyError):
                    result['QTY'] = None
                
                result['REMRAK'] = 'DONE'
                return result
    
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            print(f"Error in Big share allotment ConnectionError for PAN {panno}. Retrying... (Attempt {attempt + 1}/{retries})({e})")
        
        except Exception as e:
            result['REMRAK'] = "ERROR"
            return result

async def BigShare_allotment(user,IPOid,OrderType,ipo_register,ipo_name,Data):
    
    entry = Data
    
    data_length = len(entry)
    
    BigShare_company_data = BigShareDropDown()
    IPO_options_dict = BigShare_company_data
    selected_text = ipo_name
    selected_value = IPO_options_dict.get(selected_text, "")
    
    results = []
    
    ssl_context = ssl.create_default_context()
    # ssl_context.load_verify_locations(cafile=r'pemfile/_.bigshareonline.pem')
    
    # connector = aiohttp.TCPConnector(limit=10000)
    async with aiohttp.ClientSession(headers={
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Content-Type': 'application/json; charset=UTF-8',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }) as session:
        tasks = []
        for i in range(data_length):
            panno = entry[i]
            myobj = {
                'Applicationno': '',
                'Company': selected_value,
                'SelectionType': 'PN',
                'PanNo': panno,
                'txtcsdl': '',
                'txtDPID': '',
                'txtClId': '',
                'ddlType': '0',
                'lang': 'en'
            }
            result = {'PAN': panno}
            tasks.append(BigShare_fetch_allotment(session,user, myobj, panno, result,IPOid,OrderType,ssl_context))

        responses = await asyncio.gather(*tasks)
        valid_responses = [response for response in responses if response and 'error' not in response]
        # updates = []
        # for res in responses:
        #     if 'QTY' in res:
        #         if res['QTY'] != 'No data found' and res['Name'] != '':
        #             qty_sum = 0
        #             for key, value in res.items():
        #                 if key.startswith('QTY'):  # Check if the key starts with 'QTY'
        #                     qty_sum += int(value)
                            
        #             if 'QTY' in res:
        #                 updates.append({
        #                     'user': user,
        #                     'IPOid': IPOid,
        #                     'panno': res['PAN'],
        #                     'shares_alloted': qty_sum,
        #                     'OrderType': OrderType,
        #                 })
       
        # await bulk_create_or_update(updates)
        results.extend(responses)

    df = pd.DataFrame(results)
    IPO_name = ipo_name
    IPO_NAME = IPO_name.split()
    ipon = IPO_NAME[0]

    # Write to Excel using pandas
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{ipon}_{IPO_NAME[1]}_IPO_Allotment.xlsx"'
    
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='IPO Allotment')
    
    return response        

async def fetch_csrf_token(session, url,retries=3, timeout=5):
    for attempt in range(retries):
        try:
            async with session.get(url) as response:
                html_content = await asyncio.wait_for(response.text(), timeout)
                soup = BeautifulSoup(html_content, 'html.parser')
                csrf_token_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
                csrf_token_value = csrf_token_input['value']
                return csrf_token_value
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            print(f"Retrying... (Attempt {attempt + 1}/{retries})")
 
async def Purva_fetch_allotment(connector, user, selected_value, panno, result, IPOid, OrderType, ssl_context, retries=3, timeout=5):
    for attempt in range(retries):
        tknurl = 'https://www.purvashare.com/investor-service/ipo-query'
        url = "https://www.purvashare.com/investor-service/ipo-query"
        flag = 0
        try:
            async with aiohttp.ClientSession(
                connector=connector,
                connector_owner=False,
                cookie_jar=aiohttp.CookieJar(),
                headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://www.purvashare.com/investor-service/ipo-query'
                }
            ) as local_session:
                csrf_token_value = await fetch_csrf_token(local_session, tknurl)
                if not csrf_token_value:
                    continue
                
                myobj = {
                    'csrfmiddlewaretoken': csrf_token_value,
                    'company_id': selected_value,
                    'applicationNumber': '',
                    'panNumber': panno,
                    'submit': 'Search'
                }
                
                async with local_session.post(url, data=myobj, ssl=ssl_context) as response:
                    soup = await asyncio.wait_for(response.text(), timeout)
                    await asyncio.sleep(2)
                    soup = BeautifulSoup(soup, 'html.parser')
                    td_elements = soup.find('tbody')

                    if td_elements and td_elements.find('tr'):
                        td_elements = soup.find('tbody').find('tr').find_all('td')
                        labels = ['Name', 'App_Num', '', 'DPID', 'Shares Applied', 'Shares Allotted', '']

                        for label, td in zip(labels, td_elements):
                            if label:
                                if label == 'Name':
                                    result['Name'] = str(td.text)
                                    if str(td.text) == '':
                                        flag = 1
                                    
                                if label == 'DPID':
                                    result['DPID'] = str(td.text)
                                    
                                if label == 'App_Num':
                                    result['Appl.No'] = str(td.text)
                                    
                                if label == 'Shares Applied':
                                    result['Applied'] = str(td.text)
                                    
                                if label == 'Shares Allotted':
                                    result['QTY'] = str(td.text)
                                    if flag == 0:
                                        if str(td.text) >= '0':
                                            await update_database(user, IPOid, panno, int(td.text) ,OrderType)
                    else:
                        error_message = soup.find(text="Sorry, there was an error processing your request. Please try again.")
                        if error_message:
                            if attempt < retries:
                                continue
                            else:
                                result['REMRAK'] = 'ERROR'
                                return result
                        else:
                            result['REMRAK'] = 'ERROR'
                            result['QTY'] = 'No record found'
                            return result
                    
                    result['REMRAK'] = 'DONE'
                    return result
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            print(f"ConnectionError for PAN {panno}. Retrying... (Attempt {attempt + 1}/{retries})")

        except Exception as e:
            traceback.print_exc()
            result['REMRAK'] = "ERROR"
            return result

    result['REMRAK'] = 'NETWORK_ERROR'
    return result

async def Purva_allotment(user,IPOid,OrderType,ipo_register,ipo_name,Data):
    entry = Data
    data_length = len(entry)
    
    Purva_company_data = PurvaDropDown()           
    IPO_options_dict = Purva_company_data
    selected_text = ipo_name
    selected_value = IPO_options_dict.get(selected_text, "")
    
    results = []
    ssl_context = ssl.create_default_context(cafile='pemfile/purvashare.pem')
    connector = aiohttp.TCPConnector(limit=100)

    tasks = []
    try:
        for i in range(data_length):
            panno = entry[i]
            result = {'PAN': panno}
            tasks.append(Purva_fetch_allotment(connector, user, selected_value, panno, result, IPOid, OrderType, ssl_context))

        responses = await asyncio.gather(*tasks)
        # updates = []
        # for res in responses:
        #     if 'QTY' in res:
        #         if res['QTY'] != 'No Record Found' and res['Name'] != '':
        #             qty_sum = 0
        #             for key, value in res.items():
        #                 if key.startswith('QTY'):  # Check if the key starts with 'QTY'
        #                     qty_sum += int(value)

        #             if 'QTY' in res:
        #                 updates.append({
        #                     'user': user,
        #                     'IPOid': IPOid,
        #                     'panno': res['PAN'],
        #                     'shares_alloted': qty_sum,
        #                     'OrderType': OrderType,
        #                 })

        # await bulk_create_or_update(updates)
        results.extend(responses)
    finally:
        await connector.close()
    results = [res for res in results if res is not None]
    df = pd.DataFrame(results)
    IPO_name = ipo_name
    IPO_NAME = IPO_name.split()
    ipon = IPO_NAME[0]

    # Write to Excel using pandas
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{ipon}_{IPO_NAME[1]}_IPO_Allotment.xlsx"'
    
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='IPO Allotment')
    
    return response        

def encrypt_post_data(post_data_raw: str) -> str:
    key = b"8c7e9a2f1b4d6e35"
    iv  = b"f0d1a3b5c7e92846"

    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded = pad(post_data_raw.encode("latin1"), AES.block_size)
    encrypted = cipher.encrypt(padded)

    # IMPORTANT: return RAW Base64
    return base64.b64encode(encrypted).decode()

async def solve_captcha(captcha_image_data):
    # Use pytesseract to solve the captcha
    img = Image.open(io.BytesIO(captcha_image_data))
    img = img.resize((150, 50))
    img = img.crop((5, 5, 160, 55))
    img = img.resize((150, 50))
    
    resized_image_bytes = io.BytesIO()
    img.save(resized_image_bytes, format='PNG')
    base64_resized = base64.b64encode(resized_image_bytes.getvalue()).decode('utf-8')
    
    cap_pre_url =   'http://141.148.204.115:5000/predict'
    
    dataa = json.dumps({"image_base": base64_resized})
    # while True:
    response = requests.get(cap_pre_url, data=dataa)
    response = response.json()
    stqw = response['body']
    print(stqw)
    
    return stqw
    
async def Integrated_fetch_allotment(user,session, selected_value, panno, result,IPOid,OrderType,ssl_context, retries=3,timeout=5):
    url = 'https://www.integratedregistry.in/IRMS_V2/NCDAllotmentDetailsdataLaodNew_v2.aspx'
    
    captcha_url = 'https://www.integratedregistry.in/IRMS_V2/Captcha_V2.aspx'
    async with session.get(captcha_url,ssl=ssl_context) as response:
        captcha_image_data = await response.read()
        captcha_text = await solve_captcha(captcha_image_data)
    
    raw_payload = (
        f"Req=2&Comp={selected_value}"
        f"&AppNum="
        f"&Choice=3"
        f"&PANNO={panno}"
        f"&DPClit="
        f"&TYPE=IPO"
        f"&Captcha={captcha_text}" # <--- Solved code goes here
    )
    
    raw_payload = encrypt_post_data(raw_payload)
    payload = {
        "EncryptedData": raw_payload
    }
    
    for attempt in range(retries):
        flag = 0
        try:
            async with session.post(url, data=payload,ssl=ssl_context) as response:
                text = await asyncio.wait_for(response.text(), timeout)
                
                # Check for "Not Found" scenario
                if "Records Not Found" in text:
                    result['QTY'] = 'Records Not Found...!!!'
                    result['REMRAK'] = 'DONE'
                    return result
                
                else:
                    # --- FIX START: Updated Regex ---
                    # Use [^>]* to match 'leftdiv', 'leftdiv Newleftdiv', etc.
                    left_div_pattern = re.compile(r"<div class='leftdiv[^>]*'>(.*?)</div>")
                    
                    # Handle optional colon and whitespace in the right div
                    right_div_pattern = re.compile(r"<div class='rightdiv'>:?\s*(.*?)</div>")
                    # --- FIX END ---

                    left_divs = left_div_pattern.findall(text)
                    right_divs = right_div_pattern.findall(text)
                    
                    # Initialize default values to avoid KeyErrors
                    result.update({
                        'Appl.No': '', 'Category': '', 'DPID': '', 
                        'Name': '', 'Applied': '0', 'QTY': '0'
                    })

                    for left, right in zip(left_divs, right_divs):
                        key = left.strip()
                        val = right.strip()

                        if 'Application No' in key:
                            result['Appl.No'] = val
                        elif 'Category' in key:
                            result['Category'] = val
                        elif 'Dpid Client Id' in key:
                            result['DPID'] = val
                        elif 'Name' in key:
                            result['Name'] = val
                        elif 'Applied' in key:
                            result['Applied'] = val
                        elif 'Allotted' in key:
                            result['QTY'] = val
                            
                            # Trigger database update if allotment found
                            if val.isdigit() and int(val) >= 0:
                                await update_database(user, IPOid, panno, int(val), OrderType)
                    
                    result['REMRAK'] = 'DONE'
                    return result

        except Exception as e:
            print(f"Error for PAN {panno}: {e}")
            if attempt == retries - 1:
                result['REMRAK'] = 'ERROR'
                return result

async def Integrated_allotment(user, IPOid, OrderType, ipo_register, ipo_name,Data):
    entry = Data
            
    data_length = len(entry)
    
    Integrated_company_data = IntegratedDropDown()
    IPO_options_dict = Integrated_company_data
    selected_text = ipo_name
    selected_value = IPO_options_dict.get(selected_text, "")
    
    results = []
    
    ssl_context = ssl.create_default_context(cafile='pemfile/integrated.pem')
    
    async with aiohttp.ClientSession(headers={
        'Accept-Language': 'en-US,en;q=0.9',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest'
    }) as session:
        tasks = []
        for i in range(data_length):
            panno = entry[i]
            # myobj = {
            #     'Req':2,
            #     'Comp': selected_value,
            #     'AppNum': '',
            #     'PANNO': panno,
            #     'Choice': '3',
            #     'DPClit': '',
            #     'TYPE':'IPO',
            #     'Captcha':'undefined'
            # }
            result = {'PAN': panno}
            tasks.append(Integrated_fetch_allotment(user,session, selected_value, panno, result,IPOid,OrderType,ssl_context))

        responses = await asyncio.gather(*tasks)
        # updates = []
        # for res in responses:
        #     if 'QTY' in res:
        #         if res['QTY'] != 'Records Not Found...!!!' and res['Name'] != '':
        #             qty_sum = 0
        #             for key, value in res.items():
        #                 if key.startswith('QTY'):  # Check if the key starts with 'QTY'
        #                     qty_sum += int(value)
                            
        #             if 'QTY' in res:
        #                 updates.append({
        #                     'user': user,
        #                     'IPOid': IPOid,
        #                     'panno': res['PAN'],
        #                     'shares_alloted': qty_sum,
        #                     'OrderType': OrderType,
        #                 })
       
        # await bulk_create_or_update(updates)
        results.extend(responses)
    
    df = pd.DataFrame(results)
    IPO_name = ipo_name
    IPO_NAME = IPO_name.split()
    ipon = IPO_NAME[0]

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{ipon}_{IPO_NAME[1]}_IPO_Allotment.xlsx"'
    
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='IPO Allotment')
    
    return response

async def Maashitla_fetch_allotment(user,session, myobj, panno, result,IPOid,OrderType,ssl_context, retries=3,timeout=5):
    company = myobj['company']
    url = f'https://api.maashitla.com/api/public-issue/search?company_name={company}&pan={panno}'
    # url = 'https://maashitla.com/PublicIssues/Search'
    # ssl_context = ssl.create_default_context(cafile='pemfile/maashitla.pem')
    for attempt in range(retries):
        try:
            async with session.get(url, data=myobj) as response:
                data = await response.json()
                # data1 = await response.json()
                pan = data.get('pan',None)
                if pan == panno:
                    dpclitid = data.get('dpid_client_id',None)
                    result['DPID'] = dpclitid
                    appnum1 = data.get('application_no',None)
                    result['Appl.No'] = appnum1
                    name = data.get('name',None)
                    result['Name'] = name
                    share_Applied = data.get('shares_applied',None)
                    result['Applied'] = share_Applied
                    share_Alloted = data.get('shares_alloted',None)
                    result['QTY'] = share_Alloted
                    if name and name != '':
                        # if share_Alloted >= 0:
                        if share_Alloted is not None and share_Alloted >= 0:
                            await update_database(user, IPOid, panno, int(share_Alloted),OrderType)
                    result['REMRAK'] = 'DONE'
                    return result
                
                else:
                    result['QTY'] = 'Records Not Found...!!!'
                    result['REMRAK'] = 'DONE'
                    return result
        except aiohttp.ClientConnectionError:
            print(f"ConnectionError for PAN {panno}. Retrying... (Attempt {attempt + 1}/{retries})")
        except Exception as e:
            result['REMRAK'] = "ERROR"
            return result

async def Maashitla_allotment(user, IPOid, OrderType, ipo_register, ipo_name,Data):
    entry = Data
            
    data_length = len(entry)
    
    Integrated_company_data = MaashitlaDropDown()
    IPO_options_dict = Integrated_company_data
    selected_text = ipo_name
    selected_value = IPO_options_dict.get(selected_text, "")
    
    results = []
    
    ssl_context = ssl.create_default_context(cafile='pemfile/maashitla.pem')
    
    async with aiohttp.ClientSession(headers={
        'Accept':'*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest'
    }) as session:
        tasks = []
        for i in range(data_length):
            panno = entry[i]
            myobj = {
                        'company': selected_text,
                        'search': panno,
                    }
            result = {'PAN': panno}
            tasks.append(Maashitla_fetch_allotment(user,session, myobj, panno, result,IPOid,OrderType,ssl_context))

        responses = await asyncio.gather(*tasks)
        # updates = []
        # for res in responses:
        #     if 'QTY' in res:
        #         if res['QTY'] != 'Records Not Found...!!!' and res['Name'] != '':
        #             qty_sum = 0
        #             for key, value in res.items():
        #                 if key.startswith('QTY'):  # Check if the key starts with 'QTY'
        #                     qty_sum += int(value)
                            
        #             if 'QTY' in res:
        #                 updates.append({
        #                     'user': user,
        #                     'IPOid': IPOid,
        #                     'panno': res['PAN'],
        #                     'shares_alloted': qty_sum,
        #                     'OrderType': OrderType,
        #                 })
       
        # await bulk_create_or_update(updates)
        results.extend(responses)
    
    df = pd.DataFrame(results)
    IPO_name = ipo_name
    IPO_NAME = IPO_name.split()
    ipon = IPO_NAME[0]

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{ipon}_{IPO_NAME[1]}_IPO_Allotment.xlsx"'
    
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='IPO Allotment')
    
    return response

async def SkyLine_fetch_allotment(user, connector, myobj, panno, result, IPOid, OrderType, retries=3, timeout=5):
    url = 'https://www.skylinerta.com/display_application.php'
    company_val = myobj.get('company') or myobj.get('app')
    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession(
                connector=connector,
                connector_owner=False,
                cookie_jar=aiohttp.CookieJar(),
                headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            ) as local_session:
                # Step 1: POST to display_application.php with company to get csrf_token
                async with local_session.post(url, data={'company': company_val}) as response:
                    html = await asyncio.wait_for(response.text(), timeout)
                    soup = BeautifulSoup(html, 'lxml')
                    csrf_input = soup.find('input', {'name': 'csrf_token'})
                    csrf_token = csrf_input.get('value') if csrf_input else None
                
                if not csrf_token:
                    continue
                
                # Step 2: POST the query with PAN and CSRF token
                search_data = {
                    'client_id': '',
                    'application_no': '',
                    'pan': panno,
                    'company': company_val,
                    'csrf_token': csrf_token,
                    'action': 'search'
                }
                
                async with local_session.post(url, data=search_data) as response:
                    html = await asyncio.wait_for(response.text(), timeout)
                    soup = BeautifulSoup(html, 'lxml')
                    
                    resultsec = soup.find('div', class_='resultsec')
                    if resultsec is not None:
                        applicant_name = None
                        client_id = None
                        application_number = None
                        
                        for p in resultsec.find_all('p'):
                            strong = p.find('strong')
                            if strong:
                                strong_text = strong.text.strip()
                                val_text = p.text.replace(strong.text, '').strip()
                                if 'Applicant Name' in strong_text:
                                    applicant_name = val_text
                                elif 'DP IP /Client ID' in strong_text:
                                    client_id = val_text
                                elif 'Application Number' in strong_text:
                                    application_number = val_text
                                    
                        result['Name'] = applicant_name
                        result['DPID'] = client_id
                        result['Appl.No'] = application_number
                        
                        table = resultsec.find('table')
                        if table:
                            headers = [header.text.strip() for header in table.find_all('th')]
                            rows = []
                            for row in table.find_all('tr')[1:]:
                                cells = [cell.text.strip() for cell in row.find_all('td')]
                                rows.append(dict(zip(headers, cells)))
                            
                            if rows:
                                DataZip = rows[0]
                                shares_alloted = DataZip.get('Shares Alloted', '0')
                                shares_applied = DataZip.get('Shares Applied', '0')
                                status = DataZip.get('Status', '') or DataZip.get('Reason of Non Allotment', '')
                                
                                try:
                                    qty_alloted = int(float(shares_alloted))
                                except ValueError:
                                    qty_alloted = 0
                                    
                                if applicant_name:
                                    if qty_alloted >= 0:
                                        result['QTY'] = qty_alloted
                                        await update_database(user, IPOid, panno, qty_alloted, OrderType)
                                
                                result['Applied'] = shares_applied
                                result['Error Reason1'] = status
                        else:
                            result['QTY'] = 'Records Not Found...!!!'
                    else:
                        result['QTY'] = 'Records Not Found...!!!'
                    
                    result['REMRAK'] = 'DONE'
                    return result
            
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            print(f"ConnectionError for PAN {panno}. Retrying... (Attempt {attempt + 1}/{retries})")

        except Exception as e:
            result['REMRAK'] = "ERROR"
            return result

    result['REMRAK'] = 'NETWORK_ERROR'
    return result

async def SkyLine_allotment(user,IPOid,OrderType,ipo_register,ipo_name,Data):
    entry = Data
    
    data_length = len(entry)
    
    Skyline_company_data = SkyLineDropDown()   
    IPO_options_dict = Skyline_company_data
    selected_text = ipo_name
    selected_value = IPO_options_dict.get(selected_text, "")
    
    results = []
    connector = aiohttp.TCPConnector(limit=100)

    tasks = []
    try:
        for i in range(data_length):
            panno = entry[i]
            myobj = {
                'client_id': '',
                'application_no': '',
                'pan': panno,
                'app': selected_value,
                'action': 'search',
                'image': 'Search',
            }
            result = {'PAN': panno}
            tasks.append(SkyLine_fetch_allotment(user, connector, myobj, panno, result, IPOid, OrderType))

        responses = await asyncio.gather(*tasks)
        # updates = []
        # for res in responses:
        #     if 'QTY' in res:
        #         if res['QTY'] != 'Records Not Found...!!!' and res['Name'] != '':
        #             qty_sum = 0
        #             for key, value in res.items():
        #                 if key.startswith('QTY'):  # Check if the key starts with 'QTY'
        #                     qty_sum += int(value)

        #             if 'QTY' in res:
        #                 updates.append({
        #                     'user': user,
        #                     'IPOid': IPOid,
        #                     'panno': res['PAN'],
        #                     'shares_alloted': qty_sum,
        #                     'OrderType': OrderType,
        #                 })

        # await bulk_create_or_update(updates)
        results.extend(responses)
    finally:
        await connector.close()

    results = [res for res in results if res is not None]
    df = pd.DataFrame(results)
    IPO_name = ipo_name
    IPO_NAME = IPO_name.split()
    ipon = IPO_NAME[0]

    # Write to Excel using pandas
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{ipon}_{IPO_NAME[1]}_IPO_Allotment.xlsx"'
    
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='IPO Allotment')
    
    return response        

async def Cambridge_fetch_allotment(user,panno,result,IPOid,OrderType,selected_value,ssl_context,retries=3, timeout=5):
    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession(headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'X-Requested-With': 'XMLHttpRequest' 
            }) as session:
                myobj1={
                        'drpCompany' : '0',
                        'ddlUserTypes': 'PAN NO',
                        '__ASYNCPOST' : 'true',
                        'Button1':'Clear'
                    }
                url1 = 'https://ipostatus1.cameoindia.com/'
                async with session.get(url1,ssl = ssl_context) as response:
                    data1 = await asyncio.wait_for(response.text(),timeout)
                    soup = BeautifulSoup(data1, 'html.parser')
                    event_validation = soup.find('input', {'id': '__EVENTVALIDATION'})
                    viewstate_generator = soup.find('input', {'id': '__VIEWSTATEGENERATOR'})
                    viewstate = soup.find('input', {'id': '__VIEWSTATE'})
                    if not event_validation or not viewstate_generator or not viewstate:
                        if (attempt+1) == retries:
                            result['REMRAK'] = 'ERROR'
                            return result
                        else:
                            continue  # Retry if required fields are missing
                        
                    __EVENTVALIDATION = event_validation['value']
                    __VIEWSTATEGENERATOR = viewstate_generator['value']
                    __VIEWSTATE = viewstate['value']
                    captcha_img = soup.find('img',{'id': 'imgCaptcha'})
                    captcha_src = captcha_img.get('src')
                    url2 = f'https://ipostatus1.cameoindia.com/{captcha_src}'
                    async with session.get(url2) as response:
                        img_data = await response.read()
                        img = Image.open(io.BytesIO(img_data))
                        img = img.resize((150, 50))
                        img = img.crop((5, 5, 160, 55))
                        img = img.resize((150, 50))
                        
                        resized_image_bytes = io.BytesIO()
                        img.save(resized_image_bytes, format='PNG')
                        base64_resized = base64.b64encode(resized_image_bytes.getvalue()).decode('utf-8')
                        
                        cap_pre_url =   'http://141.148.204.115:5000/predict'  #  Oci Captcha Prediction
                        dataa = json.dumps({"image_base": base64_resized})
                        # while True:
                        response = requests.get(cap_pre_url, data=dataa)
                        response = response.json()
                        stqw = response['body']
                        myobj2={
                            '__EVENTVALIDATION' : __EVENTVALIDATION,
                            '__VIEWSTATEGENERATOR' : __VIEWSTATEGENERATOR,
                            '__VIEWSTATE' : __VIEWSTATE,
                            'drpCompany' : selected_value,
                            'ddlUserTypes': 'PAN NO',
                            'txtfolio': panno,
                            'txt_phy_captcha' : stqw.upper(),
                            '__ASYNCPOST' : 'true',
                            'btngenerate':'Submit',
                            'ScriptManager1':'OrdersPanel|btngenerate',
                            '__EVENTTARGET':'',
                            '__EVENTARGUMENT':'',
                        }
                            
                        async with session.post(url1, data=myobj2,ssl = ssl_context) as response:
                            data2 = await asyncio.wait_for(response.text(),timeout)
                            soup1 = BeautifulSoup(data2, 'html.parser')
                            table = soup1.find('table', {'class': 'table table-bordered text-center'})
                            if table:
                                headers = []
                                header_row = table.find('tr', {'class': 'table-success'})
                                if header_row:
                                    headers = [th.text.strip() for th in header_row.find_all('th')]
                                else:
                                    print("header Not found")
                                    
                                rows = []
                                tbody = table.find('tbody')
                                
                                if tbody:
                                    for row in tbody.find_all('tr'):
                                        cells = [td.text.strip() for td in row.find_all('td')]
                                        rows.append(dict(zip(headers, cells)))
                                else:        
                                    print("body Not found")
                                for row in rows:
                                    if row['HOLD1'] != 'NO DATA FOUND FOR THIS SEARCH KEY':
                                        result['Name'] = row['HOLD1']
                                        if row['HOLD1'] != '':
                                            result['Qty'] = row['ALLOTED_SHARES']
                                            if int(row['ALLOTED_SHARES']) >= 0:
                                                await update_database(user, IPOid, panno, int(row['ALLOTED_SHARES']),OrderType)
                                            
                                        result['Refund Amount'] = row['REFUND_AMOUNT']
                                        result['Refund Mode'] = row['REFUND_MODE']
                                        result['PJ_NO'] = row['PJ_NO']
                                        
                                    else:
                                        result['Qty'] = 'Records Not Found...!!!'
                                
                                result['REMRAK'] = 'DONE'
                                return result    
                            else:
                                print("Table not found for PAN", panno)
                                html_content = str(soup1)
                                html_content = html_content.encode().decode('unicode_escape')
                                match = re.search(r"showpop6\('(.+?)'\)", html_content)
                                if match:
                                    error_message = match.group(1)
                                    if error_message:
                                        print(f"Error message for PAN {panno}: {error_message}")
                                        result['Qty'] = error_message
                                        result['REMRAK'] = 'ERROR'
                                        return result
                                
                        
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            print(f"ConnectionError for PAN {panno}. Retrying... (Attempt {attempt + 1}/{retries})")
            # if attempt == 2:
            result['Qty'] = e
            result['REMRAK'] = 'ERROR'
            return result
        
        except:   
            traceback.print_exc()
            result['REMRAK'] = "ERROR"
            return result

async def Cambridge_allotment(user,IPOid,OrderType,ipo_register,ipo_name,Data):
    entry = Data
    
    data_length = len(entry)
    
    Cambridge_company_data = CambridgeDropDown()   
    IPO_options_dict = Cambridge_company_data
    selected_text = ipo_name
    selected_value = IPO_options_dict.get(selected_text, "")
    
    results = []
    
    ssl_context = ssl.create_default_context(cafile='pemfile/cambridge.pem')
    
    tasks = []
    for i in range(data_length):
        panno = entry[i]
        result = {'PAN': panno}
        tasks.append(Cambridge_fetch_allotment(user, panno, result,IPOid,OrderType,selected_value,ssl_context))
        
    responses = await asyncio.gather(*tasks)
    results.extend(responses)
    
    df = pd.DataFrame(results)
    IPO_name = ipo_name
    IPO_NAME = IPO_name.split()
    ipon = IPO_NAME[0]

    # Write to Excel using pandas
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{ipon}_{IPO_NAME[1]}_IPO_Allotment.xlsx"'
    
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='IPO Allotment')
    
    return response        
            
async def Mas_fetch_allotment(user, panno, result, IPOid, OrderType, selected_value, session, retries=3, timeout=10):
    url = f"https://www.masserv.com/{selected_value}"
    payload = {
        'texthn': panno,
        'DtLogin': 'Search'
    }
    for attempt in range(retries):
        try:
            async with session.post(url, data=payload, ssl=False, timeout=timeout) as response:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')
                upper_text = text.upper()
                
                if "NOT CORRECT" in upper_text or "NO RECORD FOUND" in upper_text or "NOT SUBMIT" in upper_text:
                    result['Qty'] = 'Records Not Found...!!!'
                    result['Name'] = ''
                    result['REMRAK'] = 'DONE'
                    return result

                result['Qty'] = 'Records Not Found...!!!'
                result['REMRAK'] = 'DONE'

                tables = soup.find_all('table')
                found_data = False
                for table in tables:
                    table_text = table.text.upper()
                    if "NAME" in table_text and ("ALLOT" in table_text or "SHARE" in table_text):
                        rows = table.find_all('tr')
                        for row in rows:
                            cols = [td.text.strip() for td in row.find_all(['td', 'th'])]
                            for i in range(0, len(cols), 2):
                                if i + 1 < len(cols):
                                    label = cols[i].upper()
                                    value = cols[i+1]
                                    if "NAME" in label:
                                        result['Name'] = value
                                        found_data = True
                                    elif "PAN" in label:
                                        result['PAN'] = value
                                    elif "DP ID" in label:
                                        result['DP ID'] = value
                                    elif "CLIENT ID" in label:
                                        result['Client ID'] = value
                                    elif "APPLIED" in label and "SHARE" in label:
                                        result['Shares Applied'] = value
                                    elif "ALLOT" in label and "SHARE" in label:
                                        try:
                                            if value.upper() == "NIL":
                                                qty = 0
                                            else:
                                                qty_str = "".join([c for c in value if c.isdigit()])
                                                qty = int(qty_str) if qty_str else 0
                                            
                                            result['Qty'] = qty
                                            if qty >= 0:
                                                await update_database(user, IPOid, panno, qty, OrderType)
                                            found_data = True
                                        except:
                                            pass
                                    elif "ADJUSTED" in label:
                                        result['Amount Adjusted'] = value
                                    elif "UNBLOCKED" in label:
                                        result['Amount UnBlocked'] = value
                        if found_data:
                            break
                return result
        except Exception as e:
            if attempt == retries - 1:
                result['Qty'] = str(e)
                result['REMRAK'] = 'ERROR'
                return result

async def Mas_allotment(user, IPOid, OrderType, ipo_register, ipo_name, Data):
    entry = Data
    data_length = len(entry)
    
    Mas_company_data = MasDropDown()
    selected_value = Mas_company_data.get(ipo_name, "")
    if not selected_value:
        selected_value = "ipo_search1.asp"
        
    results = []
    tasks = []
    
    async with aiohttp.ClientSession(headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }) as session:
        for i in range(data_length):
            panno = entry[i]
            result = {'PAN': panno}
            tasks.append(Mas_fetch_allotment(user, panno, result, IPOid, OrderType, selected_value, session))
            
        responses = await asyncio.gather(*tasks)
        results.extend(responses)
        
    df = pd.DataFrame(results)
    IPO_NAME = ipo_name.split()
    ipon = IPO_NAME[0]
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{ipon}_IPO_Allotment.xlsx"'
    
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='IPO Allotment')
    
    return response

async def MudraRTA_fetch_allotment(user, panno, result, IPOid, OrderType, selected_value, session, retries=3, timeout=10):
    # selected_value is the app_id extracted from ipo.php
    url = f"https://mudrarta.com/display_application.php?app={selected_value}"
    payload = {
        'app': selected_value,
        'pan': panno,
        'action': 'search',
        'image': 'Search'
    }
    for attempt in range(retries):
        try:
            async with session.post(url, data=payload, ssl=False, timeout=timeout) as response:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')
                
                # Get visible text for easier parsing
                visible_text = soup.get_text(separator=' ', strip=True)
                upper_text = visible_text.upper()
                
                found_data = False
                
                # Based on live testing, results follow a "Label : Value" pattern
                if "APPLICANT NAME" in upper_text or "SHARES ALLOTTED" in upper_text:
                    found_data = True
                    
                    # Extract Applicant Name
                    name_match = re.search(r'APPLICANT NAME\s*:\s*(.*?)(?=DP ID|APPLICATION NUMBER|PAN|SHARES|STATUS|$)', upper_text, re.S)
                    if name_match:
                        result['Name'] = name_match.group(1).strip()
                    else:
                        result['Name'] = ''
                    
                    # Extract DP ID /Client ID
                    client_match = re.search(r'DP ID\s*/CLIENT ID\s*:\s*(.*?)(?=APPLICATION NUMBER|PAN|SHARES|STATUS|$)', upper_text, re.S)
                    if client_match:
                        result['DP ID /Client ID'] = client_match.group(1).strip()
                    else:
                        result['DP ID /Client ID'] = ''
                        
                    # Extract Application Number
                    app_match = re.search(r'APPLICATION NUMBER\s*:\s*(.*?)(?=PAN|SHARES|STATUS|$)', upper_text, re.S)
                    if app_match:
                        result['Application Number'] = app_match.group(1).strip()
                    else:
                        result['Application Number'] = ''

                    # Extract Shares Applied
                    applied_match = re.search(r'SHARES APPLIED\s*:\s*(\d+)', upper_text)
                    if applied_match:
                        result['Shares Applied'] = int(applied_match.group(1))
                    else:
                        result['Shares Applied'] = ''

                    # Extract Status
                    status_match = re.search(r'STATUS\s*:\s*(ALLOTTEE|NON ALLOTTEE|[A-Z\s]+?)(?=OUR FACILITY|QUICK LINK|IMPORTANT LINKS|COPYRIGHT|$)', upper_text)
                    if status_match:
                        result['Status'] = status_match.group(1).strip()
                    else:
                        result['Status'] = ''
                        
                    # Extract Shares Allotted
                    qty_match = re.search(r'SHARES ALLOTTED\s*:\s*(\d+)', upper_text)
                    if qty_match:
                        qty = int(qty_match.group(1))
                        result['Shares Allotted'] = qty
                    else:
                        result['Shares Allotted'] = 0
                    
                    await update_database(user, IPOid, panno, result.get('Shares Allotted', 0), OrderType)
                    result['REMRAK'] = 'DONE'
                    return result

                # If no record area found
                if not found_data:
                    result['Name'] = ''
                    result['DP ID /Client ID'] = ''
                    result['Application Number'] = ''
                    result['Shares Applied'] = ''
                    result['Status'] = ''
                    result['Shares Allotted'] = ''
                    result['REMRAK'] = 'No Records Found'
                    return result

                return result
        except Exception as e:
            if attempt == retries - 1:
                result['Name'] = ''
                result['DP ID /Client ID'] = ''
                result['Application Number'] = ''
                result['Shares Applied'] = ''
                result['Status'] = ''
                result['Shares Allotted'] = ''
                result['REMRAK'] = f'ERROR: {str(e)}'
                return result

async def MudraRTA_allotment(user, IPOid, OrderType, ipo_register, ipo_name, Data):
    entry = Data
    data_length = len(entry)
    
    MudraRTA_company_data = MudraRTADropDown()
    selected_value = MudraRTA_company_data.get(ipo_name, "")
    
    results = []
    tasks = []
    
    async with aiohttp.ClientSession(headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }) as session:
        for i in range(data_length):
            panno = entry[i]
            result = {'PAN': panno}
            tasks.append(MudraRTA_fetch_allotment(user, panno, result, IPOid, OrderType, selected_value, session))
            
        responses = await asyncio.gather(*tasks)
        results.extend(responses)
    df = pd.DataFrame(results)
    
    # Reorder columns to user required sequence
    columns_order = ['PAN', 'Name', 'DP ID /Client ID', 'Application Number', 'Shares Applied', 'Status', 'Shares Allotted', 'REMRAK']
    # Filter only existing columns and maintain order
    available_cols = [col for col in columns_order if col in df.columns]
    df = df[available_cols]
    
    IPO_NAME = ipo_name.split()
    ipon = IPO_NAME[0]
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{ipon}_IPO_Allotment.xlsx"'
    
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='IPO Allotment')
    
    return response

def get_pancards(request, IPOid,OrderType,group=None,IPOType=None,InvestType=None,Rate='All'):
    if request.method == 'POST':
        Pan_chck =  request.POST.get('Pannocheck', '')
        Data = []
        Gp_Name =  group
        IPOTypefilter =  IPOType
        InvestorTypeFilter =  InvestType
        if Pan_chck == 'All Record':
            entry =  OrderDetail.objects.filter(
                    user=request.user, Order__OrderIPOName_id=IPOid ,Order__OrderType=OrderType)
        
        elif Pan_chck == 'Pending':
            entry =  OrderDetail.objects.filter(
                    user=request.user, Order__OrderIPOName_id=IPOid ,Order__OrderType=OrderType,AllotedQty__isnull=True)
        
        if Gp_Name == 'All' and IPOTypefilter == 'All' and InvestorTypeFilter == 'All':
            pass
        elif IPOTypefilter == 'All' and Gp_Name=='All':
            entry =  entry.filter(Order__InvestorType=InvestorTypeFilter)
        elif IPOTypefilter == 'All' and InvestorTypeFilter=='All':   
            entry = entry.filter(Order__OrderGroup__GroupName=Gp_Name)
        elif InvestorTypeFilter=='All' and  Gp_Name=='All':
            entry =  entry.filter(Order__OrderCategory=IPOTypefilter)
        elif IPOTypefilter == 'All':   
            entry = entry.filter(Order__OrderGroup__GroupName=Gp_Name, Order__InvestorType=InvestorTypeFilter)
        elif Gp_Name =='All':
            entry =  entry.filter(Order__OrderCategory=IPOTypefilter, Order__InvestorType=InvestorTypeFilter)
        elif InvestorTypeFilter=='All':
            entry =  entry.filter(Order__OrderCategory=IPOTypefilter, Order__OrderGroup__GroupName=Gp_Name)
        else:
            entry =  entry.filter(Order__OrderCategory=IPOTypefilter, Order__OrderGroup__GroupName=Gp_Name,Order__InvestorType=InvestorTypeFilter)
            
        if Gp_Name != 'All'  and is_valid_queryparam(Gp_Name):
            entry = entry.filter(Order__OrderGroup__GroupName = Gp_Name)
        
        if IPOTypefilter != 'All'  and is_valid_queryparam(IPOTypefilter):
            entry = entry.filter(Order__OrderCategory=IPOTypefilter)
            
        if InvestorTypeFilter != 'All'  and is_valid_queryparam(InvestorTypeFilter):
            entry = entry.filter(Order__InvestorType=InvestorTypeFilter)
        
        if Rate != 'All' and is_valid_queryparam(Rate):
            entry = entry.filter(Order__Rate=float(Rate))
        
        
        if entry is not None and entry.exists():
            for order_detail in entry:
                if order_detail.OrderDetailPANNo and order_detail.OrderDetailPANNo.PANNo:
                    Data.append(order_detail.OrderDetailPANNo.PANNo)       
        
        return JsonResponse({'pancards': list(Data)})
    return JsonResponse({'error': 'User not authenticated'}, status=401)
    
    
def IPO_Allotment(request,IPOid,OrderType,group=None,IPOType=None,InvestType=None,Rate='All'):
    if request.method == "POST":
        ipo_register =  request.POST.get('ipo_register', '')
        ipo_name =  request.POST.get('secondary_dropdown', '')
        Pan_chck =  request.POST.get('Pannocheck', '')
        panlist =  request.POST.get('pancards', '')
        if panlist:
            panlist = json.loads(panlist)
        PRI_limit  = CustomUser.objects.get( username = request.user)
        is_premium_user = PRI_limit.Allotment_access    
        
        if str(is_premium_user) == 'True':
            Data = panlist
            
            if ipo_register == 'Linkin':
                user = request.user
                response = asyncio.run(linkin_allotment(user, IPOid, OrderType, ipo_register, ipo_name,Data))
                return response
                
            elif ipo_register == 'Cambridge':
                user = request.user
                now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                response = asyncio.run(Cambridge_allotment(user, IPOid, OrderType, ipo_register, ipo_name,Data))
                return response
                
            elif ipo_register == 'Kfintech':
                user = request.user
                response = asyncio.run(Kfintech_allotment(user, IPOid, OrderType, ipo_register, ipo_name,Data))
                return response
            
            elif ipo_register == 'BigShare':
                user = request.user
                response = asyncio.run(BigShare_allotment(user, IPOid, OrderType, ipo_register, ipo_name,Data))
                return response
                
            elif ipo_register == 'Purva':
                user = request.user
                response = asyncio.run(Purva_allotment(user, IPOid, OrderType, ipo_register, ipo_name ,Data))
                return response
                    
            elif ipo_register == 'SkyLine':
                user = request.user
                response = asyncio.run(SkyLine_allotment(user, IPOid, OrderType, ipo_register, ipo_name,Data))
                return response
            
            elif ipo_register == 'Integrated':
                user = request.user
                response = asyncio.run(Integrated_allotment(user, IPOid, OrderType, ipo_register, ipo_name,Data))
                return response
    
            elif ipo_register == 'Maashitla':
                user = request.user
                response = asyncio.run(Maashitla_allotment(user, IPOid, OrderType, ipo_register, ipo_name,Data))
                return response
            
            elif ipo_register == 'Mas':
                user = request.user
                response = asyncio.run(Mas_allotment(user, IPOid, OrderType, ipo_register, ipo_name,Data))
                return response

            elif ipo_register == 'MudraRTA':
                user = request.user
                response = asyncio.run(MudraRTA_allotment(user, IPOid, OrderType, ipo_register, ipo_name,Data))
                return response
    
    return redirect(f"/{IPOid}/OrderDetail/{OrderType}/All/All/All")

#  Allotment Check End ----!>
@allowed_users(allowed_roles=['Broker'])
def ChangePassword(request):
    if request.method == "POST":
        NewPassword = request.POST.get('NewPassword', '')
        ConfirmPassword = request.POST.get('ConfirmPassword', '')
        if NewPassword == ConfirmPassword:
            u = User.objects.get(username__exact=request.user)
            u.set_password(ConfirmPassword)
            u.save()
            uuser = authenticate(username=request.user,
                                 password=ConfirmPassword)

            login(request, uuser)
            products = CurrentIpoName.objects.filter(user=request.user)
            params = {'product': products}

            return render(request, 'index.html', params)

        else:
            messages.error(
                request, 'New Password and Confirm Password is not equal')
            return redirect("/")

    return redirect("/")

@allowed_users(allowed_roles=['Broker'])
def Changepassword(request):
    if request.method == "POST":
        NewPassword = request.POST.get('NewPassword', '')
        ConfirmPassword = request.POST.get('ConfirmPassword', '')
        if NewPassword == ConfirmPassword:
            u = CustomUser.objects.get(username =request.user)
            u.set_password(ConfirmPassword)
            u.save()
            uuser = authenticate(username=request.user,
                                 password=ConfirmPassword)

            login(request, uuser)
            products = CurrentIpoName.objects.filter(user=request.user).order_by('-id')
            ratelist = []
            for i in products:
                try:
                    Ratelistitem = RateList.objects.get(
                        user=request.user, RateListIPOName_id=i.id)
                except:
                    Ratelistitem = 0
                ratelist.append(Ratelistitem)
                
            params = {'entry': zip(products, ratelist), 'product': products}

            return render(request, 'index.html', params)

        else:
            messages.error(
                request, 'New Password and Confirm Password is not equal')
            return redirect("/")

    return redirect("/")

@allowed_users(allowed_roles=['Broker'])
def IPOSETUP(request):
    products = CurrentIpoName.objects.filter(user=request.user)
    
    page_obj = None
    try:
        page_size = request.POST.get('Ip_page_size')
        if page_size != '' and page_size != None:
            request.session['Ip_page_size'] = page_size
        else:
            page_size = request.session['Ip_page_size']
    except:
        page_size = request.session.get('Ip_page_size', 50)
    
    Data=[]
    if page_size == 'All':
        all_rows = True
        paginator = Paginator(products,len(products))
        page_number = request.GET.get('page','1')
        page_obj = paginator.get_page(page_number)
    else:
        paginator = Paginator(products, page_size)
        page_number = request.GET.get('page','1')
        page_obj = paginator.get_page(page_number)
    if products is not None and products.exists():
            
        start_index = (page_obj.number - 1) * page_obj.paginator.per_page
        
        for i,order_detail in enumerate(page_obj):
            entry_data = {
                'id':order_detail.id,
                'IPOName': order_detail.IPOName,
                'IPOType': order_detail.IPOType,
                'IPOPrice': order_detail.IPOPrice,
                'PreOpenPrice': order_detail.PreOpenPrice,
                'LotSizeRetail': order_detail.LotSizeRetail if (order_detail.LotSizeRetail is not None) else '-',
                'LotSizeSHNI': order_detail.LotSizeSHNI if (order_detail.LotSizeSHNI is not None) else '-' ,
                'LotSizeBHNI': order_detail.LotSizeBHNI if (order_detail.LotSizeBHNI is not None) else '-',
                'TotalIPOSzie':order_detail.TotalIPOSzie,
                'RetailPercentage':order_detail.RetailPercentage,
                'BHNIPercentage':order_detail.BHNIPercentage if (order_detail.BHNIPercentage is not None) else '-',
                'SHNIPercentage':order_detail.SHNIPercentage if (order_detail.SHNIPercentage is not None) else '-',
                'Remark':order_detail.Remark,
                'sr_no': start_index + i + 1
            }
            Data.append(entry_data)
            
    df = pd.DataFrame.from_records(Data)
    html_table = "<table >\n"
    html_table = "<thead><tr style='text-align: center;white-space: nowrap; width:100%' >"
    html_table += "<th scope='col' style='width:90px;'>Sr No. &nbsp;</th>"
    html_table += "<th scope='col'>Name &nbsp;</th>"
    html_table += "<th scope='col'>IPO Type &nbsp;</th>"
    html_table += "<th scope='col'>IPO Price &nbsp;</th>"
    html_table += "<th scope='col'>Pre-Open Price &nbsp;</th>"
    html_table += "<th scope='col'>Lot Retail&nbsp;</th>"
    html_table += "<th scope='col'>Lot SHNI&nbsp;</th>"
    html_table += "<th scope='col'>Lot BHNI&nbsp;</th>"
    html_table += "<th scope='col'>Total IPOSize in Cr.&nbsp;</th>"
    html_table += "<th scope='col'>Retail %&nbsp;</th>"
    html_table += "<th scope='col'>BHNI %&nbsp;</th>"
    html_table += "<th scope='col'>SHNI %&nbsp;</th>"
    html_table += "<th scope='col'>Remark&nbsp;</th>"
    html_table += "<th scope='col'>Action &nbsp;</th>"
    html_table += "</tr></thead>\n"
    html_table += "<tbody style='text-align: center;white-space: nowrap;'>"

    for i, row in df.iterrows():
        html_table += "<tr style='text-align: center;'>"
        html_table += f"<td>{row.sr_no}</td>"
        html_table += f"<td><a <a href='/{row.id}/Order'>{row.IPOName}</a></td>"
        html_table += f"<td>{row.IPOType}</td>"
        html_table += f"<td>{row.IPOPrice}</td>"
        html_table += f"<td>{row.PreOpenPrice}</td>"
        html_table += f"<td>{row.LotSizeRetail}</td>"
        html_table += f"<td>{row.LotSizeSHNI }</td>"
        html_table += f"<td>{row.LotSizeBHNI}</td>"
        html_table += f"<td>{row.TotalIPOSzie} </td>"
        html_table += f"<td>{row.RetailPercentage} </td>"
        if(row.IPOType == 'MAINBOARD'):
            html_table += f"<td>{row.BHNIPercentage} </td>"
            html_table += f"<td>{row.SHNIPercentage} </td>"
        else:
            html_table += f"<td> - </td>"
            html_table += f"<td> - </td>"
        html_table += f"<td style='white-space: normal; max-width: 250px;'>{row.Remark}</td>"
        html_table += f"<td style='white-space: nowrap;'><button onclick=\"window.location.href='edit/{ row.id }?page={page_number}';\"\
                    class='btn btn-outline-primary' style='width: 72px;'>Edit</button>\
            <button type='button' class='btn btn-outline-danger' \
                        onclick='document.getElementById('{ row.id }').style.display='block'' style='width: 72px;'\
                        data-toggle='modal' data-target='#{ row.id }'>Delete</button></td>" 
        
        html_table += "</tr>\n"
    html_table += "</tbody></table>"
    
    for i, row in df.iterrows():
        html_table += f"""
            <div class="modal fade" id="{ row.id }" tabindex="-1" role="dialog"
                    aria-labelledby="exampleModalLabel" aria-hidden="true">
                    <div class="modal-dialog" role="document">
                        <div class="modal-content">
                            <div class="modal-header" style="border-bottom: 1px solid black;">
                                <b>
                                    <h5 class="modal-title" id="exampleModalLabel">Delete IPO</h5>
                                </b>
                                <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                                    <span aria-hidden="true">&times;</span>
                                </button>
                            </div>
                            <div class="modal-body" style="white-space: normal;">
                                <center>
                                    <p>Are you sure you want to delete { row.IPOName } IPO?</p>
                                    <div class="form-row">
                                        <div class="form-group col-md-6">
                                            <button type="button" class="btn btn-outline-secondary"
                                                data-dismiss="modal" style="width: 50%;"
                                                class="cancelbtn">Cancel</button>
                                        </div>
                                        <div class="form-group col-md-6">
                                            <button type="button" class="btn btn-outline-danger" style="width: 50%;"
                                                class="deletebtn"
                                                onclick="window.location.href='delete/{ row.id }?page={page_number}';">Delete</button>
                                        </div>
                                </center>
                            </div>
                        </div>
                    </div>
                </div>
        """
    params = {'html_table': html_table,'page_obj': page_obj,'Ip_page_size':page_size}
    return render(request, 'IPOSETUP.html', params)

@allowed_users(allowed_roles=['Broker'])
def ClientSetup(request, PanNoId='None'):
    Group = GroupDetail.objects.filter(user=request.user)

    page_obj = None
    try:
        page_size = request.POST.get('client_page_size')
        if page_size != '' and page_size != None:
            request.session['client_page_size'] = page_size
        else:
            page_size = request.session['client_page_size']
    except:
        page_size = request.session.get('client_page_size', 50)
    
    try:
        group_filter = request.POST.get('group_filter')
        if group_filter != '' and group_filter != None:
            request.session['client_group_filter'] = group_filter
        else:
            group_filter = request.session.get('client_group_filter', 'All')
    except:
        group_filter = request.session.get('client_group_filter', 'All')

    products = ClientDetail.objects.filter(user=request.user)
    if group_filter != 'All':
        products = products.filter(Group__GroupName=group_filter)
    
    Data=[]
    if page_size == 'All':
        all_rows = True
        paginator = Paginator(products,len(products))
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
    else:
        paginator = Paginator(products, page_size)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
    if products is not None and products.exists():
            
        start_index = (page_obj.number - 1) * page_obj.paginator.per_page
        
        for i,order_detail in enumerate(page_obj):
            entry_data = {
                'id':order_detail.id,
                'PANNo': order_detail.PANNo,
                'Name': order_detail.Name,
                'Group': order_detail.Group,
                'ClientIdDpId': order_detail.ClientIdDpId,
                'sr_no': start_index + i + 1
            }
            Data.append(entry_data)
    df = pd.DataFrame.from_records(Data)
    html_table = "<table >\n"
    html_table = "<thead><tr style='text-align: center;white-space: nowrap;'>"
    html_table += "<th scope='col' style='width:90px;'><input type='checkbox' id='select_all_clients'> &nbsp;Sr No. &nbsp;</th>"
    html_table += "<th scope='col'>PAN No. &nbsp;</th>"
    html_table += "<th scope='col'>Name &nbsp;</th>"
    html_table += "<th scope='col'>Group &nbsp;</th>"
    html_table += "<th scope='col'>Client-ID/DP-ID &nbsp;</th>"
    html_table += "<th scope='col'>Action&nbsp;</th>"
    html_table += "</tr></thead>\n"
    html_table += "<tbody style='text-align: center;white-space: nowrap;'>"

    for i, row in df.iterrows():
        html_table += "<tr style='text-align: center;'>"
        html_table += f"<td><input type='checkbox' class='client-checkbox' value='{row.id}'>&nbsp;{row.sr_no}</td>"
        html_table += f"<td>{row.PANNo}</td>"
        html_table += f"<td>{row.Name}</td>"
        html_table += f"<td>{row.Group}</td>"
        html_table += f"<td>{row.ClientIdDpId}</td>"
        html_table += f"<td style='white-space: nowrap;'><button onclick=\"window.location.href='EditClient/{ row.id }?page={page_number}';\"\
                    class='btn btn-outline-primary' style='width: 72px;'>Edit</button>\
            <button type='button' class='btn btn-outline-danger' \
                        style='width: 72px;'\
                        data-toggle='modal' data-target='#deleteModal_{ row.id }'>Delete</button></td>" 
        
        html_table += "</tr>\n"
    html_table += "</tbody></table>"
    
    for i, row in df.iterrows():
        html_table += f"""
            <div class="modal fade" id="deleteModal_{ row.id }" tabindex="-1" role="dialog"
                aria-labelledby="exampleModalLabel" aria-hidden="true">
                <div class="modal-dialog" role="document">
                    <div class="modal-content">
                        <div class="modal-header" style="border-bottom: 1px solid black;">
                            <b>
                                <h5 class="modal-title" id="exampleModalLabel">Delete Client</h5>
                            </b>
                            <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                                <span aria-hidden="true">&times;</span>
                            </button>
                        </div>
                        <div class="modal-body"  style="white-space: normal;">
                            <center>
                                <p>Are you sure you want to delete { row.PANNo } Client?</p>
                                <div class="form-row">
                                    <div class="form-group col-md-6">
                                        <button type="button" class="btn btn-outline-secondary" data-dismiss="modal"
                                        style="width:50%;">Cancel</button>
                                    </div>
                                    <div class="form-group col-md-6">
                                        <button type="button" class="btn btn-outline-danger"
                                        style="width:50%;" onclick="window.location.href='DeleteClient/{ row.id }?page={page_number}';"
                                        autofocus="autofocus" onfocus="this.select()">Delete</button>
                                    </div>
                                </div>
                            </center>
                        </div>
                    </div>
                </div>
            </div>
        """
            
    if PanNoId != 'None':
        employee = ClientDetail.objects.get(
            id=PanNoId, user=request.user)
        params = {'html_table': html_table, 'Group': Group.order_by(
            'GroupName'), 'employee': employee,'page_obj': page_obj,'client_page_size':page_size, 'client_group_filter': group_filter }
    else:
        params = {'html_table': html_table, 'Group': Group.order_by('GroupName'),'page_obj': page_obj,'client_page_size':page_size, 'client_group_filter': group_filter}

    return render(request, 'ClientSetup.html', params)

@allowed_users(allowed_roles=['Broker'])
def BulkDeleteClients(request):
    if request.method == "POST":
        ids = request.POST.getlist('ids[]')
        
        success_count = 0
        blocked_clients = [] 
        
        for client_id in ids:
            try:
                query = OrderDetail.objects.filter(user=request.user, OrderDetailPANNo_id=client_id)
                if query.exists():
                    client = ClientDetail.objects.get(id=client_id, user=request.user)
                    ipo_names = list(query.values_list('Order__OrderIPOName__IPOName', flat=True).distinct())
                    blocked_clients.append(f"{client.PANNo}({', '.join(ipo_names)})")
                else:
                    client = ClientDetail.objects.get(id=client_id, user=request.user)
                    client.delete()
                    success_count += 1
            except ClientDetail.DoesNotExist:
                pass
        
        if success_count > 0:
            messages.success(request, f"Successfully deleted {success_count} client(s).")
        if blocked_clients:
            messages.error(request, f"{len(blocked_clients)} client(s) could not be deleted (Used in Orders): {', '.join(blocked_clients)}.")
            
        return JsonResponse({"success": True})
    return JsonResponse({"success": False}, status=400)

@allowed_users(allowed_roles=['Broker'])
def GroupSetup(request):
    products = GroupDetail.objects.filter(user=request.user)
    
    page_obj = None
    try:
        page_size = request.POST.get('Gp_page_size')
        if page_size != '' and page_size != None:
            request.session['Gp_page_size'] = page_size
        else:
            page_size = request.session['Gp_page_size']
    except:
        page_size = request.session.get('Gp_page_size', 50)
    
    Data=[]
    if page_size == 'All':
        all_rows = True
        paginator = Paginator(products,len(products))
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
    else:
        paginator = Paginator(products, page_size)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
    if products is not None and products.exists():
        
        start_index = (page_obj.number - 1) * page_obj.paginator.per_page
        
        for i,order_detail in enumerate(page_obj):
            entry_data = {
                'id':order_detail.id,
                'GroupName': order_detail.GroupName,
                'MobileNo': order_detail.MobileNo,
                'Email': order_detail.Email,
                'Address': order_detail.Address,
                'Remark': order_detail.Remark,
                'sr_no': start_index + i + 1
            }
            Data.append(entry_data)
    df = pd.DataFrame.from_records(Data)
    html_table = "<table >\n"
    html_table = "<thead><tr style='text-align: center;white-space: nowrap;'>"
    html_table += "<th scope='col' style='width:90px;'><input type='checkbox' id='select_all_groups'> &nbsp;Sr No. &nbsp;</th>"
    html_table += "<th scope='col'>Group Name &nbsp;</th>"
    html_table += "<th scope='col'>Mobile No &nbsp;</th>"
    html_table += "<th scope='col'>Email &nbsp;</th>"
    html_table += "<th scope='col'>Address &nbsp;</th>"
    html_table += "<th scope='col'>Remark &nbsp;</th>"
    html_table += "<th scope='col'>Action &nbsp;</th>"
    html_table += "</tr></thead>\n"
    html_table += "<tbody style='text-align: center;white-space: nowrap;'>"

    for i, row in df.iterrows():
        html_table += "<tr style='text-align: center;'>"
        html_table += f"<td><input type='checkbox' class='group-checkbox' value='{row.id}'>&nbsp;{row.sr_no}</td>"
        html_table += f"<td>{row.GroupName}</td>"
        html_table += f"<td>{row.MobileNo}</td>"
        html_table += f"<td>{row.Email}</td>"
        html_table += f"<td>{row.Address}</td>"
        html_table += f"<td>{row.Remark}</td>"
        html_table += f"<td style='white-space: nowrap;'><button onclick=\"window.location.href='EditGroup/{ row.id }?page={page_number}';\"\
                    class='btn btn-outline-primary' style='width: 72px;'>Edit</button>\
            <button type='button' class='btn btn-outline-danger' \
                        onclick=\"document.getElementById('{ row.id }').style.display='block'\" style='width: 72px;'\
                        data-toggle='modal' data-target='#{ row.id }'>Delete</button></td>" 
        
        html_table += "</tr>\n"
    html_table += "</tbody></table>"
    
    for i, row in df.iterrows():
        html_table += f"""
            <div class="modal fade" id="{ row.id }" tabindex="-1" role="dialog"
                        aria-labelledby="exampleModalLabel" aria-hidden="true">
                        <div class="modal-dialog">
                            <div class="modal-content">
                                <div class="modal-header" style="border-bottom: 1px solid black;">
                                    <b>
                                        <h5 class="modal-title" id="exampleModalLabel">Delete Kostak Group</h5>
                                    </b>
                                    <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                                        <span aria-hidden="true">&times;</span>
                                    </button>
                                </div>
                                <div class="modal-body" style="white-space: normal;">
                                    <center>
                                        <p>Are you sure you want to delete { row.GroupName } group?</p>
                                        <div class="form-row">
                                            <div class="form-group col-md-6">
                                                <button type="button" class="btn btn-outline-secondary" data-dismiss="modal"
                                                style="width:50%;">Cancel</button>
                                            </div>
                                            <div class="form-group col-md-6">
                                                <button type="button" class="btn btn-outline-danger"
                                                style="width:50%;" onclick="window.location.href='DeleteGroup/{ row.id }?page={page_number}';">Delete</button>
                                            </div>
                                        </div>

                                    </center>
                                </div>
                            </div>
                        </div>
                    </div>
        """
    params = {'html_table': html_table,'page_obj': page_obj,'Gp_page_size':page_size}
    return render(request, 'GroupSetup.html', params)

@allowed_users(allowed_roles=['Broker'])
def AddCustomerUser(request):
    group = GroupDetail.objects.filter(user=request.user)
    if request.method == "POST":
        try:
            username = request.POST.get('username', '')
            password = request.POST.get('password', '')
            email = request.POST.get('email', '')
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            Group1 = request.POST.get('Group', '')
            gid = GroupDetail.objects.get(
                GroupName=Group1, user=request.user).id
            user = CustomUser.objects.create_user(
                username=username, password=password, email=email, last_name=last_name, first_name=first_name, Broker_id=request.user.id, Group_id=gid)
            user.save()
            group11 = Group.objects.get(name='Customer')
            user.groups.add(group11)
            messages.success(request, "Successfully Added User")
            return redirect("/")

        except:
            messages.error(request, 'Error.')
    return render(request, 'AddCustomerUser.html', {'Group': group.order_by('GroupName')})

@allowed_users(allowed_roles=['Broker'])
def AddIPO(request):
    if request.method == "POST":
        try:
            name = request.POST.get('name', '').upper()
            CurrentIpoName.objects.get(IPOName=name, user=request.user)
            messages.error(request, 'IPO Already Exist.')

        except:
            IPOType = request.POST.get('IPOType', '')
            name = request.POST.get('name', '')
            IPOPrice = request.POST.get('IPOPrice', '')
            TotalIPOSize = request.POST.get('TotalIPOSzie', '')
            RetailPercentage = request.POST.get('RetailPercentage', '')
            LotSizeRetail = request.POST.get('LotSizeRetail', '')
            Remark = request.POST.get('Remark', '')

            if(IPOType == 'MAINBOARD'):
                LotSizeSHNI = request.POST.get('LotSizeSHNI')     
                LotSizeBHNI = request.POST.get('LotSizeBHNI')
                SHNIPercentage = request.POST.get('SHNIPercentage', '')
                BHNIPercentage = request.POST.get('BHNIPercentage', '')
            else:
                LotSizeSHNI = None
                LotSizeBHNI = None
                SHNIPercentage = ''
                BHNIPercentage = ''
            
            currentiponame = CurrentIpoName(
                user=request.user, IPOType=IPOType, IPOName=name, IPOPrice=IPOPrice, LotSizeRetail=LotSizeRetail,LotSizeSHNI=LotSizeSHNI, LotSizeBHNI=LotSizeBHNI, TotalIPOSzie=TotalIPOSize, BHNIPercentage=BHNIPercentage, SHNIPercentage=SHNIPercentage,RetailPercentage=RetailPercentage, Remark=Remark, PreOpenPrice=IPOPrice)
            
            user = request.user
            O_limit  = CustomUser.objects.get( username = user)
            
            if O_limit.IPO_limit is not None :
            
                user = request.user
                IPO_Count = CurrentIpoName.objects.filter(user=user).count()
                IPO_Limit = int(O_limit.IPO_limit)
                
                if IPO_Count >= IPO_Limit:
                    messages.error(request, f"You have reached the limit of {IPO_Limit} IPO Limits.")
                    return redirect('/IPOSETUP')
            
            currentiponame.save()
            messages.success(request, 'IPO Added successfully.')
            return redirect("/IPOSETUP")
    return redirect("/IPOSETUP")

@allowed_users(allowed_roles=['Broker'])
def AddGroup(request):
    if request.method == "POST":
        try:
            GroupName = request.POST.get('GroupName', '').upper()
            groupdetail = GroupDetail.objects.get(
                GroupName=GroupName, user=request.user)
            messages.error(request, 'Group Already Exist.')

        except:
            GroupName = request.POST.get('GroupName', '').strip()
            Email = request.POST.get('Email','')
            if Email:
                try:
                    validate_email(Email)
                except:
                    messages.error(request, 'Invalid email format.')
                    return redirect("/GroupSetup")
                
            MobileNo = request.POST.get('MobileNo', '')
            if MobileNo:
                if len(MobileNo)!= 10 or not MobileNo.isdigit():
                    # messages.error(request, 'Invalid Mobile No.')
                    messages.error(request, 'Invalid Mobile Number. Please enter exactly 10 digits.')
                    return redirect("/GroupSetup")
                # elif len(MobileNo) == 10:
                    
                    
            Address = request.POST.get('Address', '')
            Remark = request.POST.get('Remark', '')
            groupdetail = GroupDetail(
                user=request.user, GroupName=GroupName, MobileNo=MobileNo, Address=Address, Remark=Remark,Email=Email)
            
            user = request.user
            O_limit  = CustomUser.objects.get( username = user)
            
            if O_limit.Group_limit is not None :
            
                user = request.user
                Group_Count = GroupDetail.objects.filter(user=user).count()
                Gropu_Limit = int(O_limit.Group_limit)
                
                if Group_Count >= Gropu_Limit:
                    messages.error(request, f"You have reached the limit of {Gropu_Limit} Group Limits.")
                    return redirect('/GroupSetup')
            
            groupdetail.save()
            messages.success(request, 'Group Added successfully.')
            return redirect("/GroupSetup")
    return redirect("/GroupSetup")

@allowed_users(allowed_roles=['Broker'])
def AddGroupFromPlaceOrder(request, IPOid, Action):
    if request.method == "POST":
        user = request.user
        O_limit  = CustomUser.objects.get( username = user)
        try:
            GroupName = request.POST.get('GroupName', '').strip().upper()
            groupdetail = GroupDetail.objects.get(
                GroupName=GroupName, user=request.user)
            messages.error(request, 'Group Already Exist.')

        except:
            GroupName = request.POST.get('GroupName', '').strip().upper()
            groupdetail = GroupDetail(
                user=request.user, GroupName=GroupName)
            if O_limit.Group_limit is not None :
                Group_Count = GroupDetail.objects.filter(user=user).count()
                Gropu_Limit = int(O_limit.Group_limit)
                if Group_Count >= Gropu_Limit:
                    messages.error(request, f"You have reached the limit of {Gropu_Limit} Group Limits.")
                    if Action == "BUY":
                        return redirect(f"/{IPOid}/BUY")
                    elif Action == "SELL":
                        return redirect(f"/{IPOid}/SELL")
            groupdetail.save()
        if Action == "BUY":
            return redirect(f"/BUY/{IPOid}/{GroupName}")
        elif Action == "SELL":
            return redirect(f"/SELL/{IPOid}/{GroupName}")
        else:
            return redirect("/")
        
@allowed_users(allowed_roles=['Broker'])
def DownloadGroupSample(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="Sample_Group_Upload.csv"'

    writer = csv.writer(response)
    writer.writerow(['GroupName', 'MobileNo', 'Email', 'Address', 'Remark'])
    
    return response

@allowed_users(allowed_roles=['Broker'])
def BulkUploadGroup(request):
    if request.method == "POST" and request.FILES.get('file'):
        file = request.FILES['file']
        
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.name.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file)
            else:
                messages.error(request, 'Invalid file format. Please upload a .csv, .xls, or .xlsx file.')
                return redirect("/GroupSetup")
                
            required_columns = ['GroupName']
            if not all(col in df.columns for col in required_columns):
                messages.error(request, 'Invalid file structure. Column "GroupName" is missing.')
                return redirect("/GroupSetup")
            
            # Replace NaNs with empty string
            df = df.fillna('')
            
            success_count = 0
            duplicate_count = 0
            error_count = 0
            
            user = request.user
            O_limit = CustomUser.objects.get(username=user)
            Gropu_Limit = int(O_limit.Group_limit) if O_limit.Group_limit is not None else float('inf')

            for index, row in df.iterrows():
                GroupName = str(row.get('GroupName', '')).strip().upper()
                if not GroupName:
                    error_count += 1
                    continue
                
                # Check for limit
                Group_Count = GroupDetail.objects.filter(user=user).count()
                if Group_Count >= Gropu_Limit:
                    messages.error(request, f"You have reached your limit of {Gropu_Limit} Group Limits. Process stopped.")
                    break
                
                # Check for duplicates
                if GroupDetail.objects.filter(GroupName=GroupName, user=user).exists():
                    duplicate_count += 1
                    continue
                
                # Process Email
                Email = str(row.get('Email', '')).strip()
                if Email:
                    try:
                        validate_email(Email)
                    except ValidationError:
                        Email = '' # ignore invalid emails
                        
                # Process MobileNo
                MobileNo = str(row.get('MobileNo', '')).strip()
                # remove .0 from floats
                if MobileNo.endswith('.0'): 
                    MobileNo = MobileNo[:-2]
                if MobileNo and (len(MobileNo) != 10 or not MobileNo.isdigit()):
                    MobileNo = '' # ignore invalid mobile numbers
                
                Address = str(row.get('Address', '')).strip()
                Remark = str(row.get('Remark', '')).strip()
                
                try:
                    groupdetail = GroupDetail(
                        user=user, 
                        GroupName=GroupName, 
                        MobileNo=MobileNo, 
                        Address=Address, 
                        Remark=Remark,
                        Email=Email
                    )
                    groupdetail.save()
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    print(e)

            if success_count > 0:
                messages.success(request, f'Successfully added {success_count} groups.')
            if duplicate_count > 0:
                messages.info(request, f'Skipped {duplicate_count} duplicate groups.')
            if error_count > 0:
                messages.error(request, f'Failed to add {error_count} invalid entries.')

        except Exception as e:
            messages.error(request, f'Error processing file: {str(e)}')
            
    return redirect("/GroupSetup")        


@allowed_users(allowed_roles=['Broker'])
def AddClient(request):
    Group = GroupDetail.objects.filter(user=request.user)
    if request.method == "POST":
        try:
            PANNo = request.POST.get('PANNo', '').upper()
            ClientDetail.objects.get(PANNo=PANNo.upper(), user=request.user)
            messages.error(request, 'Client Already Exist.')

        except:
            PANNo = request.POST.get('PANNo', '')
            Name = request.POST.get('Name', '')
            Group = request.POST.get('Group', '')
            ClientIdDpId = request.POST.get('ClientIdDpId', '')
            gid = GroupDetail.objects.get(
                GroupName=Group, user=request.user).id
            currentiponame = ClientDetail(user=request.user, PANNo=PANNo.upper(
            ), Name=Name, Group_id=gid, ClientIdDpId=ClientIdDpId)
            
            user = request.user
            O_limit  = CustomUser.objects.get( username = user)
            
            if O_limit.Client_limit is not None :
            
                user = request.user
                Client_Count = ClientDetail.objects.filter(user=user).count()
                Client_Limit  = int(O_limit.Client_limit)

                if Client_Count >= Client_Limit:
                    messages.error(request, f"You have reached the limit of {Client_Limit} Client limits.")
                    return redirect('/ClientSetup')
            
            currentiponame.save()
            messages.success(request, 'Client Added successfully.')
            return redirect("/ClientSetup")
    return redirect("/ClientSetup")

@allowed_users(allowed_roles=['Broker'])
def edit(request, IPOid):
    page_number = request.GET.get('page','1')
    employee = CurrentIpoName.objects.get(
        id=IPOid, user=request.user)
    return render(request, 'edit.html', {'employee': employee,'page_number':page_number})

@allowed_users(allowed_roles=['Broker'])
def EditClient(request, PanNoId):
    page_number = request.GET.get('page','1')
    Group = GroupDetail.objects.filter(user=request.user)

    employee = ClientDetail.objects.get(
        id=PanNoId, user=request.user)
    return render(request, 'EditClient.html', {'employee': employee, 'Group': Group.order_by('GroupName'),'page_number':page_number})

@allowed_users(allowed_roles=['Broker'])
def EditGroup(request, GroupNameId):
    page_number = request.GET.get('page','1')

    employee = GroupDetail.objects.get(
        id=GroupNameId, user=request.user)
    return render(request, 'EditGroup.html', {'employee': employee,'page_number':page_number})

def EditOrder(request, OrderId,IPOid,Grpf,OrCtf,InTyf):
    page_number = request.GET.get('page')
    order = Order.objects.get(OrderIPOName_id = IPOid,
        id=OrderId, user=request.user)
    Group = GroupDetail.objects.filter(user=request.user)
    Group_sorted = sorted(Group, key=lambda x: x.GroupName)
    IPO = CurrentIpoName.objects.get(id=IPOid, user=request.user)
    return render(request, 'EditOrder.html', {'employee': order,'Group': Group_sorted,'Grpf':Grpf,'OrCtf':OrCtf,'InTyf':InTyf,'IPOid':IPOid,'IPOName':IPO,'page_number':page_number})

#ipo update fun
@allowed_users(allowed_roles=['Broker'])
def update(request, IPOid):
    page_number = request.GET.get('page','1')
    employee = CurrentIpoName.objects.get(
        id=IPOid, user=request.user)
    n = 1
    if request.method == "POST":
        if n == 1:
            name = request.POST.get('name', '').upper()
            for j in CurrentIpoName.objects.filter(user=request.user).values('IPOName'):
                if name == j.get('IPOName'):
                    if name != employee.IPOName:
                        messages.error(request, 'IPO Already Exist.')
                        n = 0
                        break
            if n == 0:
                return redirect(f"/edit/{IPOid}")
        if n == 1:
            IPOType =  request.POST.get('IPOType', '')
            name = request.POST.get('name', '')
            IPOPrice = request.POST.get('IPOPrice', '')
            LotSizeRetail = request.POST.get('LotSizeRetail', '')  
            TotalIPOSize = request.POST.get('TotalIPOSize', '')
            RetailPercentage = request.POST.get('RetailPercentage', '')
            Remark = request.POST.get('Remark', '')            
            if IPOType == 'MAINBOARD':
                LotSizeBHNI = request.POST.get('LotSizeBHNI')
                LotSizeSHNI = request.POST.get('LotSizeSHNI')
                BHNIPercentage = request.POST.get('BHNIPercentage')
                SHNIPercentage = request.POST.get('SHNIPercentage')
            else:
                LotSizeBHNI = None
                LotSizeSHNI = None
                BHNIPercentage = ''
                SHNIPercentage = ''
            
            employee.IPOType = IPOType
            employee.IPOName = name
            employee.IPOPrice = IPOPrice
            employee.LotSizeRetail = LotSizeRetail            
            employee.TotalIPOSzie = TotalIPOSize
            employee.RetailPercentage = RetailPercentage            
            employee.Remark = Remark
            employee.LotSizeBHNI = LotSizeBHNI
            employee.LotSizeSHNI = LotSizeSHNI
            employee.BHNIPercentage = BHNIPercentage
            employee.SHNIPercentage = SHNIPercentage
            
            employee.save()
            messages.success(request, 'IPO Edit successfully.')
            return redirect(f"/IPOSETUP?page={page_number}")
    return render(request, 'edit.html', {'employee': employee})

def updatepreopenprice_calculate(IPOid, user, Orderid=None):
    # 1. Fetch IPOName once
    try:
        IPOName = CurrentIpoName.objects.get(id=IPOid, user=user)
    except CurrentIpoName.DoesNotExist:
        return

    # 2. Setup Filters
    detail_filter = {"user": user, "Order__OrderIPOName_id": IPOid}
    order_filter = {"user": user, "OrderIPOName_id": IPOid}
    
    if Orderid:
        detail_filter["Order_id"] = Orderid
        order_filter["id"] = Orderid

    # 3. Initial Reset (Efficient SQL update)
    OrderDetail.objects.filter(**detail_filter).update(Amount=0)
    Order.objects.filter(**order_filter).update(Amount=0)

    # 4. Process OrderDetails (Kostak & Subject To)
    # select_related('Order') is CRITICAL for performance
    entry_qs = OrderDetail.objects.filter(**detail_filter).select_related('Order').iterator()
    
    entries_to_update = []
    order_running_totals = {} # key: order_id, value: sum of entry amounts
    orders_map = {} # to keep track of Order objects for bulk update
    
    ipo_price = float(IPOName.IPOPrice or 0)

    for i in entry_qs:
        order = i.Order
        key = order.id
        
        # Initialize running total for this order if not seen
        if key not in order_running_totals:
            order_running_totals[key] = 0
            orders_map[key] = order

        calc_amount = 0.0
        pre_open = float(i.PreOpenPrice or 0)
        alloted_qty = float(i.AllotedQty or 0)
        order_rate = float(order.Rate or 0)

        # Logic for Kostak
        if order.OrderCategory == 'Kostak':
            if i.AllotedQty is not None:
                diff = (pre_open - ipo_price) * alloted_qty
                calc_amount = diff - order_rate
                if order.OrderType == "SELL":
                    calc_amount = -1 * calc_amount
            else:
                calc_amount = 0

        # Logic for Subject To
        elif order.OrderCategory == 'Subject To':
            if i.AllotedQty is not None and alloted_qty != 0:
                final_rate = (order_rate * alloted_qty) if order.Method == "Premium" else order_rate
                diff = (pre_open - ipo_price) * alloted_qty
                calc_amount = diff - final_rate
                if order.OrderType == "SELL":
                    calc_amount = -1 * calc_amount
            else:
                calc_amount = 0

        i.Amount = calc_amount
        order_running_totals[key] += calc_amount
        entries_to_update.append(i)

        # Periodic bulk update to save memory
        if len(entries_to_update) >= 5000:
            OrderDetail.objects.bulk_update(entries_to_update, ['Amount'])
            entries_to_update = []

    # Final bulk update for remaining entries
    if entries_to_update:
        OrderDetail.objects.bulk_update(entries_to_update, ['Amount'])

    # 5. Process Orders (Premium, CALL, PUT + Updated Totals)
    orders_to_update = []
    order_qs = Order.objects.filter(**order_filter)
    
    ipo_pre_open = float(IPOName.PreOpenPrice or 0)

    for o in order_qs:
        # If this order had details (Kostak/Subject To), use the sum we calculated
        if o.id in order_running_totals:
            o.Amount = order_running_totals[o.id]
        
        # Standalone logic for other categories
        qty = float(o.Quantity or 0)
        rate = float(o.Rate or 0)
        try:
            method_val = float(o.Method)
        except (ValueError, TypeError):
            method_val = 0


        if o.OrderCategory == 'Premium':
            val = (ipo_pre_open - (ipo_price + rate)) * qty
            o.Amount = val if o.OrderType == "BUY" else (-1 * val)
        
        elif o.OrderCategory == 'CALL':
            diff = (ipo_pre_open - (ipo_price + method_val)) * qty
            if o.OrderType == "BUY":
                diff_paid = max(0, diff)
                o.Amount = (qty * (-1 * rate)) + diff_paid
            else: # SELL
                diff_paid = min(0, (ipo_price + method_val - ipo_pre_open) * qty)
                o.Amount = (qty * rate) + diff_paid

        elif o.OrderCategory == 'PUT':
            diff = (ipo_price + method_val - ipo_pre_open) * qty
            if o.OrderType == "BUY":
                diff_paid = max(0, diff)
                o.Amount = (qty * (-1 * rate)) + diff_paid
            else: # SELL
                diff_paid = min(0, (ipo_pre_open - (ipo_price + method_val)) * qty)
                o.Amount = (qty * rate) + diff_paid

        orders_to_update.append(o)

    # Bulk update all orders
    if orders_to_update:
        Order.objects.bulk_update(orders_to_update, ['Amount'])

@allowed_users(allowed_roles=['Broker'])
def updatepreopenprice(request, IPOid,group,IPOType,InvestType):
    Groupfilter = unquote(group)
    IPOTypefilter = unquote(IPOType)
    InvestTypefilter = unquote(InvestType)
    employee = CurrentIpoName.objects.get(
        id=IPOid, user=request.user)
    entry = OrderDetail.objects.filter(
        user=request.user, Order__OrderIPOName_id=IPOid)
    
    if request.method == "POST":
        UpdatePreOpenPrice = request.POST.get('PreOpenPrice', '')
        selected_ids = request.POST.get('selected_ids', '')
        if selected_ids:
            id_list = [s_id for s_id in selected_ids.split(",") if s_id.strip()]
            entry.filter(id__in=id_list).update(PreOpenPrice=UpdatePreOpenPrice)
            updatepreopenprice_calculate(IPOid, request.user)
        else:
            employee.PreOpenPrice = UpdatePreOpenPrice
            entry.update(PreOpenPrice = UpdatePreOpenPrice)
            employee.save()
        updatepreopenprice_calculate(IPOid, request.user)
        return redirect(f"/{IPOid}/Billing/{Groupfilter}/{IPOTypefilter}/{InvestTypefilter}")
       
    return redirect(f"/{IPOid}/Billing/{Groupfilter}/{IPOTypefilter}/{InvestTypefilter}")

@sync_to_async
def Entry_calculate_update(i,IPOName):
    if i.Order.OrderCategory == 'Kostak':
        if i.AllotedQty == None:
            i.Amount = 0
            i.save()
            return
        else:
            AllotedQty = i.AllotedQty
        
        if i.Order.OrderType == "BUY":
            i.Order.Amount = i.Order.Amount + ((float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                                                * float(AllotedQty)) - i.Order.Rate
            i.Amount = ((float(i.PreOpenPrice) - float(IPOName.IPOPrice))* float(AllotedQty)) - i.Order.Rate
        if i.Order.OrderType == "SELL":
            i.Order.Amount = i.Order.Amount + (-1*(((float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                                                    * float(AllotedQty)) - i.Order.Rate))
            i.Amount = (-1*(((float(i.PreOpenPrice) - float(IPOName.IPOPrice))* float(AllotedQty)) - i.Order.Rate))

    if i.Order.OrderCategory == 'Subject To':
        if i.AllotedQty == None:
            i.Amount = 0
            i.save()
            return
        else:
            AllotedQty = i.AllotedQty
        if(AllotedQty != 0):
            if i.Order.Method == "Premium":
                Order_rate = i.Order.Rate * float(AllotedQty)
            else:
                Order_rate = i.Order.Rate
            
            if i.Order.OrderType == "BUY":
                i.Order.Amount = i.Order.Amount + ((float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                                                    * float(AllotedQty)) - Order_rate
                i.Amount = ((float(i.PreOpenPrice) - float(IPOName.IPOPrice))* float(AllotedQty)) - Order_rate

            if i.Order.OrderType == "SELL":
                i.Order.Amount = i.Order.Amount + (-1*(((float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                                                        * float(AllotedQty)) - Order_rate))
                i.Amount = (-1*(((float(i.PreOpenPrice) - float(IPOName.IPOPrice))* float(AllotedQty)) - Order_rate))

        else:
            i.Order.Amount = i.Order.Amount + 0
    
    i.Order.save()
    i.save()

async def Entry_calculate_update_sync(i,IPOName):
    await Entry_calculate_update(i,IPOName)

@sync_to_async
def Order_calculate_update(i,IPOName):
    if i.OrderCategory == 'Premium':
        if i.OrderType == "BUY":
            i.Amount = (float(IPOName.PreOpenPrice) -
                        (float(IPOName.IPOPrice) + float(i.Rate))) * int(i.Quantity)
        if i.OrderType == "SELL":
            i.Amount = (-1*((float(IPOName.PreOpenPrice) -
                             (float(IPOName.IPOPrice) + float(i.Rate))) * int(i.Quantity)))
        i.save()
    # pass

async def Order_calculate_update_sync(j,IPOName):
    await Order_calculate_update(j,IPOName)

async def entry_Order_Update(entry,order,IPOName):
    Entry_tasks = []
    Order_tasks = []
    for i in entry:
        Entry_tasks.append(Entry_calculate_update_sync(i,IPOName))
        
    await asyncio.gather(*Entry_tasks)
        
    for j in order:
        Order_tasks.append(Order_calculate_update_sync(j,IPOName))
    
    await asyncio.gather(*Order_tasks)
    
def entry_order_Calculate_sync(entry,order,IPOName):
    async_to_sync(entry_Order_Update)(entry,order,IPOName)

def calculate(IPOid,user,Orderid=None):
    
    if Orderid is None:
        entry = OrderDetail.objects.filter(
            user=user, Order__OrderIPOName_id=IPOid).select_related('Order')
        order = Order.objects.filter(
            user=user, OrderIPOName_id=IPOid )
 
    else:
        entry = OrderDetail.objects.filter(
            user=user, Order__OrderIPOName_id=IPOid, Order_id = Orderid).select_related('Order')
        order = Order.objects.filter(
            user=user, OrderIPOName_id=IPOid , id=Orderid)
    IPOName = CurrentIpoName.objects.get(id=IPOid, user=user)
    
    order.update(Amount=0)
    # for e in entry:
    #     e.Amount = 0
    #     e.save()
    entry.update(Amount=0)
    # for o in order:
    #     o.Amount = 0
    #     o.save()
    
    # entry_order_Calculate_sync(entry,order,IPOName)
    
    orders_to_update = []
    entries_to_update = []
    
    amount = {}
    order_update = {}
    
    for i in entry:
        key = i.Order.id
        if key not in amount:
            amount[key] = 0
            i_amount = i.Order.Amount
        else:
            i_amount = amount[key]
        
        
        if i.Order.OrderCategory == 'Kostak':
            if i.AllotedQty == None:
                i.Amount = 0
                # i.save()
                entries_to_update.append(i)
                continue
            else:
                AllotedQty = i.AllotedQty
            if i.Order.OrderType == "BUY":
                i_amount = i_amount + ((float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                                                   * float(AllotedQty)) - i.Order.Rate
                i.Amount = ((float(i.PreOpenPrice) - float(IPOName.IPOPrice))* float(AllotedQty)) - i.Order.Rate
            if i.Order.OrderType == "SELL":
                i_amount = i_amount + (-1*(((float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                                                        * float(AllotedQty)) - i.Order.Rate))
                i.Amount = (-1*(((float(i.PreOpenPrice) - float(IPOName.IPOPrice))* float(AllotedQty)) - i.Order.Rate))

        if i.Order.OrderCategory == 'Subject To':
            if i.AllotedQty == None:
                i.Amount = 0
                entries_to_update.append(i)
                # i.save()
                continue
            else:
                AllotedQty = i.AllotedQty
            if(AllotedQty != 0):
                if i.Order.Method == "Premium":
                    Order_rate = i.Order.Rate * float(AllotedQty)
                else:
                    Order_rate = i.Order.Rate
                if i.Order.OrderType == "BUY":
                    
                    i_amount = i_amount + ((float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                                                       * float(AllotedQty)) - Order_rate
                    i.Amount = ((float(i.PreOpenPrice) - float(IPOName.IPOPrice))* float(AllotedQty)) - Order_rate

                if i.Order.OrderType == "SELL":
                    i_amount = i_amount + (-1*(((float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                                                            * float(AllotedQty)) - Order_rate))
                    i.Amount = (-1*(((float(i.PreOpenPrice) - float(IPOName.IPOPrice))* float(AllotedQty)) - Order_rate))

            else:
                i_amount = i_amount + 0
        
        # i.Order.save()
        # i.save()
        
        i.Order.Amount = i_amount
        amount[key] = i_amount
        order_update[key] = i.Order
            
        entries_to_update.append(i)
        
    orders_to_update = list(order_update.values())
    
        
    for i in order:
        if i.OrderCategory == 'Premium':
            if i.OrderType == "BUY":
                i.Amount = (float(IPOName.PreOpenPrice) -
                            (float(IPOName.IPOPrice) + float(i.Rate))) * int(i.Quantity)
            if i.OrderType == "SELL":
                i.Amount = (-1*((float(IPOName.PreOpenPrice) - (float(IPOName.IPOPrice) + float(i.Rate))) * int(i.Quantity)))
            # i.save()
            orders_to_update.append(i)
            
        elif i.OrderCategory == 'CALL':
            if i.OrderType == "BUY":
                diff = (float(IPOName.PreOpenPrice) - (float(IPOName.IPOPrice) + float(i.Method))) * float(i.Quantity)
                if diff < 0:
                    diff_paid = 0 
                else:
                    diff_paid = diff
                i.Amount = (float(i.Quantity) * (-1*float(i.Rate)) ) + diff_paid
            
            if i.OrderType == "SELL":
                diff = ((float(IPOName.IPOPrice) + float(i.Method) - float(IPOName.PreOpenPrice) )) * float(i.Quantity)
                if diff > 0:
                    diff_paid = 0 
                else:
                    diff_paid = diff
                i.Amount = (float(i.Quantity) * float(i.Rate) ) + diff_paid
                
            # i.save()
            orders_to_update.append(i)
            
        elif i.OrderCategory == 'PUT':
            if i.OrderType == "BUY":
                diff = ((float(IPOName.IPOPrice) + float(i.Method) - float(IPOName.PreOpenPrice) )) * float(i.Quantity)
                if diff < 0:
                    diff_paid = 0 
                else:
                    diff_paid = diff
                i.Amount = (float(i.Quantity) * (-1*float(i.Rate)) ) + diff_paid
                
            if i.OrderType == "SELL":
                diff = (float(IPOName.PreOpenPrice) - (float(IPOName.IPOPrice) + float(i.Method))) * float(i.Quantity)
                if diff > 0:
                    diff_paid = 0 
                else:
                    diff_paid = diff
                i.Amount = (float(i.Quantity) * float(i.Rate) ) + diff_paid
            
            # i.save()
            orders_to_update.append(i)
            
     
    Order.objects.bulk_update(orders_to_update, ['Amount'], batch_size=1000)
    OrderDetail.objects.bulk_update(entries_to_update, ['Amount'], batch_size=1000)
                
def panupload_calculate(IPOid, userid, Orderid=None):
    if Orderid is None or not isinstance(Orderid, list):
        Orderid = [Orderid] if Orderid is not None else []

    if Orderid:
        entry_qs = OrderDetail.objects.filter(
            user_id=userid, Order__OrderIPOName_id=IPOid, Order_id__in=Orderid)
        order_qs = Order.objects.filter(
            user_id=userid, OrderIPOName_id=IPOid, id__in=Orderid)
    else:
        entry_qs = OrderDetail.objects.filter(
            user_id=userid, Order__OrderIPOName_id=IPOid)
        order_qs = Order.objects.filter(
            user_id=userid, OrderIPOName_id=IPOid)

    try:
        IPOName = CurrentIpoName.objects.get(id=IPOid, user_id=userid)
    except CurrentIpoName.DoesNotExist:
        return

    # Update orders and entries amounts to zero initially
    order_qs.update(Amount=0)
    entry_qs.update(Amount=0)

    updated_orders_dict = {}
    updated_entries = []
    entry_list = list(entry_qs.select_related('Order'))
    
    for i in entry_list:
        order_obj = i.Order
        order_key = order_obj.id
        
        if order_key not in updated_orders_dict:
            order_obj.Amount = 0
            updated_orders_dict[order_key] = order_obj
        
        target_order = updated_orders_dict[order_key]
        
        if order_obj.OrderCategory == 'Kostak':
            if i.AllotedQty is None:
                i.Amount = 0
                updated_entries.append(i)
                continue
            AllotedQty = i.AllotedQty
            if order_obj.OrderType == "BUY":
                amount_calc = ((float(i.PreOpenPrice) - float(IPOName.IPOPrice)) * float(AllotedQty)) - order_obj.Rate
                target_order.Amount += amount_calc
                i.Amount = amount_calc
            if order_obj.OrderType == "SELL":
                amount_calc = (-1 * (((float(i.PreOpenPrice) - float(IPOName.IPOPrice)) * float(AllotedQty)) - order_obj.Rate))
                target_order.Amount += amount_calc
                i.Amount = amount_calc

        elif order_obj.OrderCategory == 'Subject To':
            if i.AllotedQty is None:
                i.Amount = 0
                updated_entries.append(i)
                continue
            AllotedQty = i.AllotedQty
            if AllotedQty != 0:
                Order_rate = order_obj.Rate * float(AllotedQty) if order_obj.Method == "Premium" else order_obj.Rate
                if order_obj.OrderType == "BUY":
                    amount_calc = ((float(i.PreOpenPrice) - float(IPOName.IPOPrice)) * float(AllotedQty)) - Order_rate
                    target_order.Amount += amount_calc
                    i.Amount = amount_calc
                if order_obj.OrderType == "SELL":
                    amount_calc = (-1 * (((float(i.PreOpenPrice) - float(IPOName.IPOPrice)) * float(AllotedQty)) - Order_rate))
                    target_order.Amount += amount_calc
                    i.Amount = amount_calc
            else:
                target_order.Amount += 0
        
        updated_entries.append(i)
    
    # Handle Premium orders
    for i in order_qs.filter(OrderCategory='Premium'):
        if i.OrderType == "BUY":
            i.Amount = (float(IPOName.PreOpenPrice) - (float(IPOName.IPOPrice) + float(i.Rate))) * int(i.Quantity)
        elif i.OrderType == "SELL":
            i.Amount = (-1 * ((float(IPOName.PreOpenPrice) - (float(IPOName.IPOPrice) + float(i.Rate))) * int(i.Quantity)))
        updated_orders_dict[i.id] = i
    
    # Perform bulk updates
    if updated_orders_dict:
        Order.objects.bulk_update(list(updated_orders_dict.values()), ['Amount'])
    if updated_entries:
        OrderDetail.objects.bulk_update(updated_entries, ['Amount'])

def EditOrderPreOpenPrice(request, IPOid ,OrderDetailId,  OrderCategory, InvestorType,group,IPOType,InvestType):
    # orderpreopen = OrderDetail.objects.get(user=request.user, id=OrderDetailId)
    page_number = request.GET.get('page','1')
    if request.method == "POST":
        PreOpenPrice = request.POST.get('PreOpenPrice', '')
        selected_ids = request.POST.get('selected_ids', '')
        if selected_ids:
            # Bulk update
            id_list = selected_ids.split(',')
            for s_id in id_list:
                if s_id:
                    try:
                        order_detail = OrderDetail.objects.get(user=request.user, id=s_id)
                        order_detail.PreOpenPrice = PreOpenPrice
                        order_detail.save()
                        # Recalculate for each updated row
                        UdatepreopenpriceAmount(request.user, IPOid, s_id, order_detail.Order.OrderCategory, order_detail.Order.InvestorType)
                    except Exception:
                        continue
        else:
            # Single update (existing logic)
            orderpreopen = OrderDetail.objects.get(user=request.user, id=OrderDetailId)    
            orderpreopen.PreOpenPrice = PreOpenPrice
            orderpreopen.save()
            UdatepreopenpriceAmount(request.user,IPOid ,OrderDetailId,OrderCategory,InvestorType)  
            
        return redirect(f"/{IPOid}/Billing/{group}/{IPOType}/{InvestType}?page={page_number}")

    return redirect(f"/{IPOid}/Billing/{group}/{IPOType}/{InvestType}?page={page_number}")

def UdatepreopenpriceAmount(user,IPOid,OrderDetailId,OrderCategory,InvestorType):
    
    entry = OrderDetail.objects.filter(id=OrderDetailId,
        user=user, Order__OrderIPOName_id=IPOid)

    O_IPO_p = OrderDetail.objects.get(id=OrderDetailId, user=user,Order__OrderIPOName_id=IPOid)

    IPOName = CurrentIpoName.objects.get(id=IPOid, user=user)
   
    for i in entry:
        if OrderCategory == "Kostak":
            if i.Order.InvestorType == InvestorType: 
                if i.AllotedQty == None:
                    i.Amount = 0
                    i.save()
                    continue
                else:
                    AllotedQty = i.AllotedQty
                if i.Order.OrderType == "BUY":
                    i.Order.Amount = (i.Order.Amount + ((float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                                                        * float(AllotedQty)) - i.Order.Rate) -i.Amount
                    i.Amount = ((float(i.PreOpenPrice) - float(IPOName.IPOPrice))* float(AllotedQty)) - i.Order.Rate
                
                if i.Order.OrderType == "SELL":
                    i.Order.Amount = (i.Order.Amount + (-1*(((float(i.PreOpenPrice) - float(IPOName.IPOPrice))

                                                    * float(AllotedQty)) - i.Order.Rate)) )-i.Amount
                    i.Amount = (-1*(((float(i.PreOpenPrice) - float(IPOName.IPOPrice))* float(AllotedQty)) - i.Order.Rate))
        
        if OrderCategory == "Subject To":
            if i.Order.InvestorType == InvestorType: 
                if i.AllotedQty == None:
                    i.Amount = 0
                    i.save()
                    continue
                else:
                    AllotedQty = i.AllotedQty
                    
                if i.Order.Method == "Premium":
                    Order_rate = i.Order.Rate * float(AllotedQty)
                else:
                    Order_rate = i.Order.Rate    
                
                if i.Order.OrderType == "BUY":
                    i.Order.Amount = (i.Order.Amount + ((float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                                                    * float(AllotedQty)) - Order_rate)-i.Amount
                    i.Amount = ((float(i.PreOpenPrice) - float(IPOName.IPOPrice))* float(AllotedQty)) - Order_rate
                
                if i.Order.OrderType == "SELL":
                    i.Order.Amount = (i.Order.Amount + (-1*(((float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                                                    * float(AllotedQty)) - Order_rate))) -i.Amount
                    i.Amount = (-1*(((float(i.PreOpenPrice) - float(IPOName.IPOPrice))* float(AllotedQty)) - Order_rate))
            else:
                i.Order.Amount = i.Order.Amount + 0
            
        i.Order.save()
        i.save()
        
@allowed_users(allowed_roles=['Broker'])
def UpdateClient(request, PANNoId):
    page_number = request.GET.get('page','1')
    employee = ClientDetail.objects.get(
        id=PANNoId, user=request.user)
    n = 1
    if request.method == "POST":
        if n == 1:
            PanNo = request.POST.get('PANNo', '').upper()

            for j in ClientDetail.objects.filter(user=request.user).values('PANNo'):
                if PanNo == j.get('PANNo'):
                    if PanNo != employee.PANNo:
                        messages.error(request, 'Client Already Exist.')
                        n = 0
                        break
            if n == 0:
                return redirect(f"/EditClient/{PANNoId}?page={page_number}")
        if n == 1:
            PANNo = request.POST.get('PANNo', '')
            Name = request.POST.get('Name', '')
            Group = request.POST.get('Group', '')
            gid = GroupDetail.objects.get(
                GroupName=Group, user=request.user).id
            ClientIdDpId = request.POST.get('ClientIdDpId', '')
            Remark = request.POST.get('Remark', '')
            employee.PANNo = PANNo.upper()
            employee.Name = Name
            employee.Group_id = gid
            employee.ClientIdDpId = ClientIdDpId
            employee.Remark = Remark
            employee.save()
            return redirect(f"/ClientSetup?page={page_number}")
    return render(request, 'EditClient.html', {'employee': employee})

@allowed_users(allowed_roles=['Broker'])
def UpdateGroup(request, GroupNameId):
    page_number = request.GET.get('page','1')

    employee = GroupDetail.objects.get(
        id=GroupNameId, user=request.user)
    n = 1
    if request.method == "POST":
        if n == 1:
            Groupname = request.POST.get('GroupName', '').strip().upper()

            for j in GroupDetail.objects.filter(user=request.user).values('GroupName'):
                if Groupname == j.get('GroupName'):
                    if Groupname != employee.GroupName:
                        messages.error(request, 'Group Already Exist.')
                        n = 0
                        break
            if n == 0:
                return redirect(f"/EditGroup/{GroupNameId}")
        if n == 1:
            GroupName = request.POST.get('GroupName', '')
            MobileNo = request.POST.get('MobileNo', '')
            if MobileNo:
                if len(MobileNo)!= 10 or not MobileNo.isdigit():
                    # messages.error(request, 'Invalid Mobile No.')
                    messages.error(request, 'Invalid Mobile Number. Please enter exactly 10 digits.')
                    return redirect("/GroupSetup")
            Address = request.POST.get('Address', '')
            Email = request.POST.get('Email','')
            if Email:
                try:
                    validate_email(Email)
                except:
                    messages.error(request,'Invalid email format.')
                    return redirect(f"/EditGroup/{GroupNameId}")
            Remark = request.POST.get('Remark', '')
            employee.GroupName = GroupName
            employee.MobileNo = MobileNo
            employee.Address = Address
            employee.Email = Email
            employee.Remark = Remark
            employee.save()
            return redirect(f"/GroupSetup?page={page_number}")
    return render(request, 'EditGroup.html', {'employee': employee})


@allowed_users(allowed_roles=['Broker'])
def destroy(request, IPOid):
    
    try:
        url = request.GET.get('url')
        user = request.user
        page_number = request.GET.get('page', '1')
        
        ipo = CurrentIpoName.objects.get(id=IPOid, user=user)
        orders = Order.objects.filter(user=user, OrderIPOName=IPOid)
        transactions = Accounting.objects.filter(
            user=user, ipo=IPOid, is_deleted=False
        )
        # 🟢 Step 2: Group by user group name and SUM Amount
        grouped_sums = []
        # total_amount = orders.aggregate(total=Sum('Amount'))['total'] or 0
        total_amount = round(orders.aggregate(total=Sum('Amount'))['total'] or 0, 1)
        
        
        creditsamount = transactions.filter(amount_type='credit').aggregate(total=Sum('amount'))['total'] or 0
        debitsamount = transactions.filter(amount_type='debit').aggregate(total=Sum('amount'))['total'] or 0
        
        ipo_collection = total_amount - round(float(creditsamount) - float(debitsamount) , 1)
        
        if ipo_collection != 0:
            messages.error(request, f"IPO '{ipo.IPOName}' cannot be deleted as it has a non-zero collection amount of {ipo_collection}. Please settle all transactions before deletion.")
            return redirect(url or 'IPOSETUP')
        # Delete related records
        OrderDetail.objects.filter(user=request.user, Order__OrderIPOName_id=IPOid).delete()
        RateList.objects.filter(user=request.user, RateListIPOName_id=IPOid).delete()
        Order.objects.filter(user=request.user, OrderIPOName_id=IPOid).delete()

        # # Update Accounting: keep ipo_name text, set ipo FK = None
        ipo = CurrentIpoName.objects.get(id=IPOid, user=request.user)
        Accounting.objects.filter(ipo=ipo, user=request.user).update(
            ipo_name=ipo.IPOName,
            status=True,
            ipo=None
        )
        ipo_name_str = ipo.IPOName
        # Finally delete IPO
        ipo.delete()
        if url:
            target_url = url    
        else:
            target_url = f"/IPOSETUP?page={page_number}"
        messages.success(request, f"IPO '{ipo_name_str}' successfully deleted.")
        return redirect(url or f"/IPOSETUP?page={page_number}")

    except CurrentIpoName.DoesNotExist:
        messages.error(request, "IPO not found!")
        # return JsonResponse({"success": False, "message": "IPO not found!"}, status=404)
        return redirect(url or 'IPOSETUP')
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(traceback_str)
        return redirect(url or 'IPOSETUP')

@allowed_users(allowed_roles=['Broker'])
def DeleteClient(request, PANNoId):
    page_number = request.GET.get('page','1')
    query = OrderDetail.objects.filter(user=request.user, OrderDetailPANNo_id=PANNoId)
    if query.exists():
        ipo_names = list(query.values_list('Order__OrderIPOName__IPOName', flat=True).distinct())
        client = ClientDetail.objects.get(id=PANNoId, user=request.user)
        messages.error(
            request, f"Client-{client.PANNo} ({client.Name}) cannot be deleted as it has order(s) in: {', '.join(ipo_names)}. First remove these order(s).")
    else:
        employee = ClientDetail.objects.get(
            id=PANNoId, user=request.user)
        employee.delete()
        messages.success(request, "Client deleted successfully.")
    return redirect(f"/ClientSetup?page={page_number}")

@allowed_users(allowed_roles=['Broker'])
def DeleteAllClient(request):
    # if request.method == "POST":
    page_number = request.GET.get('page','1')
    group_filter = request.session.get('client_group_filter', 'All')
    
    clients_to_delete = ClientDetail.objects.filter(user=request.user)
    if group_filter != 'All':
        clients_to_delete = clients_to_delete.filter(Group__GroupName=group_filter)
        
    pan_data = []
    # protected_pans = []
    for client in clients_to_delete:
        query = OrderDetail.objects.filter(user=request.user, OrderDetailPANNo_id=client.id)
        if not query.exists():
            pan_data.append({'PAN': client.PANNo, 'Status': 'Deleted'})
            client.delete()
        else:
            # protected_pans.append(str(client.PANNo))
            ipo_names = list(query.values_list('Order__OrderIPOName__IPOName', flat=True).distinct())
            pan_data.append({'PAN': client.PANNo, 'Status': f'Not Deleted (Used in: {", ".join(ipo_names)})'})
            
    df = pd.DataFrame(pan_data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='PAN Deletion Status')
    output.seek(0)
    
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="PAN_Deletion_Status.xlsx"'
    response.set_cookie('download_complete', '1', max_age=10)  # <- Add this
    return response
        
    
    # if protected_pans:
    #     messages.error(request, f"These PANs were not deleted as they are used in orders: {', '.join(protected_pans)}")
        
    # return redirect(f"/ClientSetup?page={page_number}")
    # else:
    #     return redirect(f"/ClientSetup?page={page_number}")
    # if OrderDetail.objects.filter(user=request.user, OrderDetailPANNo_id=PANNoId):
    #     PANNo = ClientDetail.objects.get(
    #         id=PANNoId, user=request.user)
    #     messages.error(
    #         request, f"Client-{PANNo} cannot be deleted as it has order(s) In Any IPO. First Remove Order(s).")
    # else:
    #     employee = ClientDetail.objects.get(
    #         id=PANNoId, user=request.user)
    #     employee.delete()


@allowed_users(allowed_roles=['Broker'])
def DeleteGroup(request, GroupNameId):
    page_number = request.GET.get('page','1')

    GroupName = GroupDetail.objects.get(
        id=GroupNameId, user=request.user)
    if ClientDetail.objects.filter(Group_id=GroupNameId).exists():
        messages.error(
            request, f"Group {GroupName} cannot be deleted as it has client(s). First Remove Client(s).")
    elif Order.objects.filter(user=request.user, OrderGroup_id=GroupNameId):
        messages.error(
            request, f"Group {GroupName} cannot be deleted as it has created order(s). First Remove Order(s).")
    else:
        Accounting.objects.filter(group_id=GroupNameId, user=request.user).update(
            group_name=GroupName.GroupName,
            status=True,
            group_id=None
        )
        employee = GroupDetail.objects.get(
            id=GroupNameId, user=request.user)
        employee.delete()
    return redirect(f"/GroupSetup?page={page_number}")

@allowed_users(allowed_roles=['Broker'])
def BulkDeleteGroup(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            group_ids = data.get('group_ids', [])
            if not group_ids:
                return JsonResponse({'status': 'error', 'message': 'No groups selected.'})
            
            # Optimized: Fetch all groups in one query instead of looping queries
            groups_to_process = GroupDetail.objects.filter(id__in=group_ids, user=request.user)
            
            deleted_count = 0
            blocked_count = 0
            blocked_reasons = []

            for group in groups_to_process:
                gid = group.id
                if ClientDetail.objects.filter(Group_id=gid).exists():
                    blocked_count += 1
                    blocked_reasons.append(f"{group.GroupName} (has clients)")
                elif Order.objects.filter(user=request.user, OrderGroup_id=gid).exists():
                    blocked_count += 1
                    blocked_reasons.append(f"{group.GroupName} (has orders)")
                else:
                    # Update Accounting history before deletion to capture name
                    Accounting.objects.filter(group_id=gid, user=request.user).update(
                        group_name=group.GroupName,
                        status=True,
                        group_id=None
                    )
                    group.delete()
                    deleted_count += 1

            # Professional pluralization for summary messages
            success_txt = "group" if deleted_count == 1 else "groups"
            msg = f"Successfully deleted {deleted_count} {success_txt}."
            
            if blocked_count > 0:
                blocked_txt = "group" if blocked_count == 1 else "groups"
                msg += f" {blocked_count} {blocked_txt} could not be deleted: {', '.join(blocked_reasons)}."
            
            if deleted_count > 0:
                messages.success(request, msg)
            elif blocked_count > 0:
                messages.error(request, msg)

            return JsonResponse({'status': 'success', 'deleted_count': deleted_count, 'blocked_count': blocked_count})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})

@allowed_users(allowed_roles=['Broker'])
def DeleteOrder(request, IPOid, OrderId, GrpName, OrderCategory, InvestorType):
    page_number = request.GET.get('page','1')
    employee = OrderDetail.objects.filter(
        Order_id=OrderId, user=request.user)
    employee.delete()
    ord = Order.objects.get(
        id=OrderId, user=request.user)
    ord_grp = ord.OrderGroup
    ord.delete()
    last_order = Order.objects.filter(
        OrderIPOName=IPOid,
        user=request.user,
        OrderGroup__GroupName=ord_grp
    ).order_by('-id').first()  # Use `-id` to get the latest by ID (or `-created_at` if timestamp exists)
    if last_order:
        last_order.Telly = "False"
        last_order.save()
    
    return redirect(f"/{IPOid}/Order/{GrpName}/{OrderCategory}/{InvestorType}?page={page_number}")

@csrf_exempt
@allowed_users(allowed_roles=['Broker'])
def BulkDeleteOrders(request, IPOid):
    if request.method == "POST":
        data = json.loads(request.body)
        order_ids = data.get('order_ids', [])
        
        if not order_ids:
            return JsonResponse({'status': 'error', 'message': 'No orders selected.'})

        try:
            ipo_int_id = int(IPOid)
        except ValueError:
            return JsonResponse({'status': 'error', 'message': f'Invalid IPO ID: {IPOid}'})

        with transaction.atomic():
            # Get groups affected before deletion
            affected_groups = list(Order.objects.filter(
                id__in=order_ids, 
                user=request.user
            ).values_list('OrderGroup_id', flat=True).distinct())
            
            # Delete OrderDetail records first
            OrderDetail.objects.filter(Order_id__in=order_ids, user=request.user).delete()
            # Delete Order records
            Order.objects.filter(id__in=order_ids, user=request.user).delete()
            
            # Update Telly status for affected groups
            for group_id in affected_groups:
                last_order = Order.objects.filter(
                    OrderIPOName_id=ipo_int_id,
                    user=request.user,
                    OrderGroup_id=group_id
                ).order_by('-id').first()
                if last_order:
                    last_order.Telly = "False"
                    last_order.save()
        
        return JsonResponse({'status': 'success', 'message': f'Successfully deleted {len(order_ids)} orders.'})
        
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=400)


@allowed_users(allowed_roles=['Broker', 'Customer'])
def BUY(request, IPOid, selectgroup=None):
    userid = request.user
    uid = request.user
    entry = GroupDetail.objects.filter(user=userid)

    product = Order.objects.filter(
            user=userid, OrderIPOName_id=IPOid).order_by('-id')

    IPOName = CurrentIpoName.objects.get(id=IPOid, user=userid)
    IPOType = IPOName.IPOType
    PreOpenPrice = IPOName.PreOpenPrice
    
    Ratelist = RateList(user=userid, RateListIPOName=IPOName, kostakBuyRate=0, KostakBuyQty=0,
                            SubjecToBuyRate=0, SubjecToBuyQty=0, PremiumBuyRate=0, PremiumBuyQty=0)
    if request.method == "POST":
        user = request.user
        Group = request.POST.get('item_id', '')

        gid = GroupDetail.objects.get(GroupName=Group, user=userid).id
        KostakRate = request.POST.get('KostakRate', '')
        SubjectToRate = request.POST.get('SubjectToRate', '')
        PremiumRate = request.POST.get('PremiumRate', '')

        KostakRateBHNI = request.POST.get('KostakRateBHNI', '')
        SubjectToRateBHNI = request.POST.get('SubjectToRateBHNI', '')
    
        KostakRateSHNI = request.POST.get('KostakRateSHNI', '')
        SubjectToRateSHNI = request.POST.get('SubjectToRateSHNI', '')

        KostakQTY = request.POST.get('KostakQTY', '')
        SubjectToQTY = request.POST.get('SubjectToQTY', '')
        KostakQTYSHNI = request.POST.get('KostakQTYSHNI', '')
        SubjectToQTYSHNI = request.POST.get('SubjectToQTYSHNI', '')
        KostakQTYBHNI = request.POST.get('KostakQTYBHNI', '')
        SubjectToQTYBHNI = request.POST.get('SubjectToQTYBHNI', '')
        PremiumQTY = request.POST.get('PremiumQTY', '')  
        
        CallQty = request.POST.get('CallQTY', '')
        CallRate = request.POST.get('CallRate', '')
        CallStrikePrice = request.POST.get('CallStrikePrice', '')
        
        PutQTY = request.POST.get('PutQTY', '')
        PutRate = request.POST.get('PutRate', '')
        PutStrikePrice = request.POST.get('PutStrikePrice', '')
        placeOrderOnly = request.POST.get('placeOrderOnly', False)

        DateTime = request.POST.get('datetime', '')
        OrderDate = DateTime[0:10]
        OrderTime = DateTime[11:19]


        # Extract remark data from tags input and text field
        remark_tags_str = request.POST.get('remark_tags', '').strip()
        remark_text = request.POST.get('remark_text', '').strip()
        
        # Build remark JSON
        remark_json = {}
        if remark_tags_str:
            try:
                import json
                remark_tags = json.loads(remark_tags_str)
                if remark_tags:  # If there are any tags
                    remark_json['tags'] = remark_tags
            except json.JSONDecodeError:
                pass  # If JSON parsing fails, skip tags
        
        if remark_text:
            remark_json['text'] = remark_text
        
        # Set to None if empty
        remark_json = remark_json if remark_json else None


        a = 0
        if KostakQTY != '' and KostakQTY != "0" and KostakRate != '':
            order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType = 'RETAIL',
                          OrderCategory='Kostak', OrderType="BUY", Quantity=KostakQTY, Rate=KostakRate, OrderDate=OrderDate, OrderTime = OrderTime, remark=remark_json)
            
            O_limit  = CustomUser.objects.get( username = user)
            if O_limit.Order_limit is not None :
                BUY_Count = OrderDetail.objects.filter(user=user,Order__OrderIPOName_id= IPOid).count()
                Sum_Qty = int(BUY_Count) + int(KostakQTY)
                Limit  = int(O_limit.Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(request, f"You have reached the limit of {Limit} OrderDetail.")
                    return redirect(f'/{IPOid}/BUY')
            try:
                order.save()
                a = 1

                # Order_Details_update_sync(KostakQTY, uid, order.id, PreOpenPrice)
                
                orderdetails = [
                    OrderDetail(user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice)
                    for _ in range(int(KostakQTY))
                ]
                OrderDetail.objects.bulk_create(orderdetails)
            except:
                a==0
                
        if KostakQTYSHNI != '' and KostakQTYSHNI != "0" and KostakRateSHNI != '':
            order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType = 'SHNI',
                          OrderCategory='Kostak', OrderType="BUY", Quantity=KostakQTYSHNI, Rate=KostakRateSHNI, OrderDate=OrderDate, OrderTime = OrderTime, remark=remark_json)
            
            O_limit  = CustomUser.objects.get( username = user)
            if O_limit.Order_limit is not None :
                BUY_Count = OrderDetail.objects.filter(user=user , Order__OrderIPOName_id= IPOid).count()
                Sum_Qty = int(BUY_Count) + int(KostakQTYSHNI)
                Limit  = int(O_limit.Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(request, f"You have reached the limit of {Limit} OrderDetail.")
                    return redirect(f'/{IPOid}/BUY')
            try:
                order.save()
                a = 1
                
                orderdetails = [
                    OrderDetail(user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice)
                    for _ in range(int(KostakQTYSHNI))
                ]
                OrderDetail.objects.bulk_create(orderdetails)
            except:
                a==0
                
        if KostakQTYBHNI != '' and KostakQTYBHNI != "0" and KostakRateBHNI != '':
            order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType = 'BHNI',
                          OrderCategory='Kostak', OrderType="BUY", Quantity=KostakQTYBHNI, Rate=KostakRateBHNI, OrderDate=OrderDate, OrderTime = OrderTime, remark=remark_json)
            
            O_limit  = CustomUser.objects.get( username = user)
            if O_limit.Order_limit is not None :
                BUY_Count = OrderDetail.objects.filter(user=user , Order__OrderIPOName_id= IPOid).count()
                Sum_Qty = int(BUY_Count) + int(KostakQTYBHNI)
                Limit  = int(O_limit.Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(request, f"You have reached the limit of {Limit} OrderDetail.")
                    return redirect(f'/{IPOid}/BUY')
            try:
                order.save()
                a = 1

                orderdetails = [
                    OrderDetail(user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice)
                    for _ in range(int(KostakQTYBHNI))
                ]
                OrderDetail.objects.bulk_create(orderdetails)
            except:
                a==0
        
        if SubjectToQTY != '' and SubjectToQTY != "0" and SubjectToRate != '':
            if request.POST.get('subjectToIsPremiumRetail', '') != None and request.POST.get('subjectToIsPremiumRetail', '') != '' and  request.POST.get('subjectToIsPremiumRetail', '') == 'on':
                order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType = 'RETAIL',
                          OrderCategory='Subject To', OrderType="BUY", Quantity=SubjectToQTY, Rate=SubjectToRate, OrderDate=OrderDate, OrderTime = OrderTime,Method = 'Premium', remark=remark_json)
            else:    
                order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType = 'RETAIL',
                            OrderCategory='Subject To', OrderType="BUY", Quantity=SubjectToQTY, Rate=SubjectToRate, OrderDate=OrderDate, OrderTime = OrderTime, remark=remark_json)
            
            O_limit  = CustomUser.objects.get( username = user)
            if O_limit.Order_limit is not None :
                BUY_Count = OrderDetail.objects.filter(user=user , Order__OrderIPOName_id= IPOid).count()
                Sum_Qty = int(BUY_Count) + int(SubjectToQTY)
                Limit  = int(O_limit.Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(request, f"You have reached the limit of {Limit} OrderDetail.")
                    return redirect(f'/{IPOid}/BUY')
            try:
                order.save()
                a = 1
                orderdetails = [
                    OrderDetail(user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice)
                    for _ in range(int(SubjectToQTY))
                ]
                OrderDetail.objects.bulk_create(orderdetails)
            except:
                a==0
        if SubjectToQTYSHNI != '' and SubjectToQTYSHNI != "0" and SubjectToRateSHNI != '':
            if request.POST.get("subjectToIsPremiumSHNI",'') !=None and request.POST.get("subjectToIsPremiumSHNI",'') != '' and request.POST.get("subjectToIsPremiumSHNI",'') == 'on':
                order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType = 'SHNI',
                            OrderCategory='Subject To', OrderType="BUY", Quantity=SubjectToQTYSHNI, Rate=SubjectToRateSHNI, OrderDate=OrderDate, OrderTime = OrderTime,Method = 'Premium', remark=remark_json)
            else:
                order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType = 'SHNI',
                            OrderCategory='Subject To', OrderType="BUY", Quantity=SubjectToQTYSHNI, Rate=SubjectToRateSHNI, OrderDate=OrderDate, OrderTime = OrderTime, remark=remark_json)
            
            O_limit  = CustomUser.objects.get( username = user)
            if O_limit.Order_limit is not None :
                BUY_Count = OrderDetail.objects.filter(user=user , Order__OrderIPOName_id= IPOid).count()
                Sum_Qty = int(BUY_Count) + int(SubjectToQTYSHNI)
                Limit  = int(O_limit.Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(request, f"You have reached the limit of {Limit} OrderDetail.")
                    return redirect(f'/{IPOid}/BUY')
            try:
                order.save()
                a = 1
                orderdetails = [
                    OrderDetail(user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice)
                    for _ in range(int(SubjectToQTYSHNI))
                ]
                OrderDetail.objects.bulk_create(orderdetails)
            except:
                a==0
        if SubjectToQTYBHNI != '' and SubjectToQTYBHNI != "0" and SubjectToRateBHNI != '':
            if request.POST.get("subjectToIsPremiumBHNI",'') !=None and request.POST.get("subjectToIsPremiumBHNI",'') != '' and request.POST.get("subjectToIsPremiumBHNI",'') == 'on':
                order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType = 'BHNI',
                            OrderCategory='Subject To', OrderType="BUY", Quantity=SubjectToQTYBHNI, Rate=SubjectToRateBHNI, OrderDate=OrderDate, OrderTime = OrderTime,Method = 'Premium', remark=remark_json)
            else:
                order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType = 'BHNI',
                            OrderCategory='Subject To', OrderType="BUY", Quantity=SubjectToQTYBHNI, Rate=SubjectToRateBHNI, OrderDate=OrderDate, OrderTime = OrderTime, remark=remark_json)
            
            O_limit  = CustomUser.objects.get( username = user)
            if O_limit.Order_limit is not None :
                BUY_Count = OrderDetail.objects.filter(user=user , Order__OrderIPOName_id= IPOid).count()
                Sum_Qty = int(BUY_Count) + int(SubjectToQTYBHNI)
                Limit  = int(O_limit.Order_limit)
                
                if Sum_Qty >= Limit + 1:
                    messages.error(request, f"You have reached the limit of {Limit} OrderDetail.")
                    return redirect(f'/{IPOid}/BUY')
            try:
                order.save()
                a = 1
                orderdetails = [
                    OrderDetail(user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice)
                    for _ in range(int(SubjectToQTYBHNI))
                ]
                OrderDetail.objects.bulk_create(orderdetails)
            except:
                a==0

        if PremiumQTY != '' and PremiumQTY != "0" and PremiumRate != '':
            order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType ='PREMIUM',
                            OrderCategory='Premium', OrderType="BUY", Quantity=PremiumQTY, Rate=PremiumRate, OrderDate=OrderDate, OrderTime = OrderTime, remark=remark_json)
            
            O_limit  = CustomUser.objects.get( username = user)
            if O_limit.Premium_Order_limit is not None :
                Order_type = "Premium"
                Pri_QTY = Order.objects.filter(user=user , OrderIPOName_id= IPOid , OrderCategory=Order_type).aggregate(Sum('Quantity'))['Quantity__sum'] 
                Pri_QTY = Pri_QTY if Pri_QTY is not None else 0
                Sum_Qty = int(Pri_QTY) + int(PremiumQTY)
                Limit  = int(O_limit.Premium_Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(request, f"You have reached the limit of {Limit} Premium shares QTY.")
                    return redirect(f'/{IPOid}/BUY')
            try:
                order.save()
                entry2 = Order.objects.get(user=request.user, id=order.id)
                calculate(IPOid, request.user,entry2.id)
                a = 1
            except:
                a==0
            
        if CallQty != '' and CallQty != "0" and CallRate != '' and CallStrikePrice != '':
            order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType ='OPTIONS',
                    OrderCategory='CALL', OrderType="BUY", Quantity=CallQty, Rate=CallRate, OrderDate=OrderDate, OrderTime = OrderTime,Method=CallStrikePrice, remark=remark_json)
            
            O_limit  = CustomUser.objects.get( username = user)
            if O_limit.Premium_Order_limit is not None :
                Order_type = "Premium"
                Pri_QTY = Order.objects.filter(user=user , OrderIPOName_id= IPOid , OrderCategory=Order_type).aggregate(Sum('Quantity'))['Quantity__sum'] 
                Pri_QTY = Pri_QTY if Pri_QTY is not None else 0
                Sum_Qty = int(Pri_QTY) + int(PremiumQTY)
                Limit  = int(O_limit.Premium_Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(request, f"You have reached the limit of {Limit} Premium shares QTY.")
                    return redirect(f'/{IPOid}/BUY')
                
            try:
                order.save()
                entry2 = Order.objects.get(user=request.user, id=order.id)
                calculate(IPOid, request.user,entry2.id)
                a = 1
            except:
                a==0
                
        if PutQTY != '' and PutQTY != "0" and PutRate != '' and PutStrikePrice != '':
            order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType ='OPTIONS',
                    OrderCategory='PUT', OrderType="BUY", Quantity=PutQTY, Rate=PutRate, OrderDate=OrderDate, OrderTime = OrderTime,Method=PutStrikePrice, remark=remark_json)
            
            O_limit  = CustomUser.objects.get( username = user)
            if O_limit.Premium_Order_limit is not None :
                Order_type = "Premium"
                Pri_QTY = Order.objects.filter(user=user , OrderIPOName_id= IPOid , OrderCategory=Order_type).aggregate(Sum('Quantity'))['Quantity__sum'] 
                Pri_QTY = Pri_QTY if Pri_QTY is not None else 0
                Sum_Qty = int(Pri_QTY) + int(PremiumQTY)
                Limit  = int(O_limit.Premium_Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(request, f"You have reached the limit of {Limit} Premium shares QTY.")
                    return redirect(f'/{IPOid}/BUY')
                
            try:
                order.save()
                entry2 = Order.objects.get(user=request.user, id=order.id)
                calculate(IPOid, request.user,entry2.id)
                a = 1
            except:
                a==0
        
        if a == 1:
            if placeOrderOnly:
                messages.success(request, 'Buy order placed successfully.')
            else:
                messages.success(request, 'Buy order placed successfully. Telegram message sent successfully ')
            return JsonResponse({'status': 'success', 'message': 'BUY order placed successfully'})
            # return redirect(f'/{IPOid}/BUY')
        else:
            messages.error(request, 'Buy order was not placed. Please try again.')
            return JsonResponse({'status': 'fail', 'message': 'BUY order dose not placed'})
            
            # return redirect(f'/{IPOid}/BUY')
                        
    if selectgroup!=None:
        selectgroup=unquote(selectgroup)
    else:
        if Order.objects.count() > 0:
            selectgroup = Order.objects.latest('id').OrderGroup.GroupName
        else:
            selectgroup = None

    return render(request, 'buy.html', {'product':product
                                        ,'entry': entry.order_by('GroupName'), 'IPOid': IPOid,"order_type": "BUY", 'IPOName': IPOName, 'Ratelist': Ratelist, 'selectgroup': selectgroup})

@allowed_users(allowed_roles=['Broker'])
def UpdateOrder(request, IPOid, OrderId, Grpf, OrCtf, InTyf):
    page_number = request.GET.get('page')
    userid = request.user
    uid = request.user
    Grpf = unquote(Grpf)
    OrCtf = unquote(OrCtf)
    entry = GroupDetail.objects.filter(user=userid)
    order = Order.objects.get( user=userid, id = OrderId)
    IPOName = CurrentIpoName.objects.get(id=IPOid, user=userid)
    if request.method == "POST":
        Group = request.POST.get('Group', '')
        gid = GroupDetail.objects.get(GroupName=Group, user=userid).id
        OrderType = request.POST.get('OrderType', '')
        Qty = request.POST.get('Qty', '')
        if IPOName.IPOType != 'SME':
            InvestorType = request.POST.get('InvestorType', '')
        else:
            InvestorType ='RETAIL'
        OrderCategory = request.POST.get('OrderCategory', '')
        if OrderCategory == "Subject To":
            Rate = request.POST.get('Sub_Rate', '') 
            RateOrPremium = request.POST.get('subjectToIsPremium','')
        else:
            Rate = request.POST.get('Rate', '')
        
        if  InvestorType == 'OPTIONS':
            Strike_price = request.POST.get('optionStrikePrice','')
            
        DateTime = request.POST.get('datetime', '')
        OrderDate = DateTime[0:10]
        OrderTime = DateTime[11:19]
        var = 1
        
        
        # Extract remark data
        remark_tags_str = request.POST.get('remark_tags', '').strip()
        remark_text = request.POST.get('remark_text', '').strip()
        
        remark_json = {}
        if remark_tags_str:
            try:
                import json
                remark_tags = json.loads(remark_tags_str)
                if remark_tags:
                    remark_json['tags'] = remark_tags
            except:
                pass
        if remark_text:
            remark_json['text'] = remark_text
        
        remark_final = remark_json if remark_json else None

        try:
            if OrderCategory == 'Subject To':
                print(Order.objects.get(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType=InvestorType, Rate=Rate,
                        OrderCategory=OrderCategory, OrderType=OrderType, Quantity=Qty, OrderDate=OrderDate, OrderTime=OrderTime,Method=RateOrPremium, remark=remark_final) )
            elif InvestorType == 'OPTIONS' :
                print(Order.objects.get(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType=InvestorType, Rate=Rate,
                        OrderCategory=OrderCategory, OrderType=OrderType, Quantity=Qty, OrderDate=OrderDate, OrderTime=OrderTime,Method=Strike_price, remark=remark_final) )
            else:
                print(Order.objects.get(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType=InvestorType, Rate=Rate,
                        OrderCategory=OrderCategory, OrderType=OrderType, Quantity=Qty, OrderDate=OrderDate, OrderTime=OrderTime, remark=remark_final))
        except:
            var = 0
            entry = Order.objects.get(user=request.user, id=OrderId)
            orderdetailfilter = OrderDetail.objects.filter(user=request.user, Order_id=OrderId, OrderDetailPANNo = None)
            orderdetail = orderdetailfilter.count()
            entry.OrderGroup_id = gid
            entry.OrderIPOName = IPOName
            entry.InvestorType = InvestorType
            entry.OrderCategory = OrderCategory
            if OrderCategory == 'Subject To':
                if RateOrPremium != None and RateOrPremium != '' and RateOrPremium == 'on':
                    entry.Method = 'Premium'
                else:
                    entry.Method = None
                    
            if InvestorType == 'OPTIONS':
                entry.Method = Strike_price
            
            entry.OrderType = OrderType
            entry.Rate = Rate
            entry.OrderTime = OrderTime
            entry.OrderDate = OrderDate
            entry.Telly = False
            entry.remark = remark_final
            
            if order.Quantity == float(Qty):
                entry.Rate = Rate
                entry.Quantity = order.Quantity
                try:
                    entry.save()
                except:
                    var = 3
            elif order.Quantity < float(Qty):
                user = request.user
                O_limit  = CustomUser.objects.get( username = user)
                if O_limit.Order_limit is not None :
                    n = int(float(Qty)-order.Quantity)
                    BUY_Count = OrderDetail.objects.filter(user=user,Order__OrderIPOName_id= IPOid).count()
                    Sum_Qty = int(BUY_Count) + int(n)
                    Limit  = int(O_limit.Order_limit)
                    if Sum_Qty >= Limit + 1:
                        messages.error(request, f"You have reached the limit of {Limit} OrderDetail.")
                        return redirect(f"/{IPOid}/Order/{Grpf}/{OrCtf}/{InTyf}?page={page_number}")    

                entry.Quantity = Qty
                try:
                    entry.save()
                except:
                    var = 3

                if OrderCategory != 'Premium' and InvestorType != 'OPTIONS':
                    n = int(float(Qty)-order.Quantity)
                    for i in range(0, n):
                        orderdetail1 = OrderDetail(user=uid, Order_id = entry.id)
                        orderdetail1.save()
            else:
                if OrderCategory != 'Premium':
                    j = 0
                    k = (order.Quantity-float(Qty))

                    if k <= orderdetail:
                        for i in orderdetailfilter:       
                            if j < k:
                                i.delete()
                                j+=1
                        entry.Quantity = Qty
                        try:
                            entry.save()
                        except:
                            var = 3

                    else:
                        var = 2
                        if InvestorType == 'OPTIONS':
                            entry.Quantity = float(Qty)
                            var = None
                        else:
                            entry.Quantity = order.Quantity
                        try:
                            entry.save()
                        except:
                            var = 3
                else:
                    entry.Quantity = Qty
                    try:
                        entry.save()
                    except:
                        var=3

            calculate(IPOid, request.user,entry.id)

        if var == 1:
            messages.error(
            request, 'Order values are same')
        elif var == 2:
            messages.success(request, 'Order Modified') 
            
            messages.error(request, 'Error : Only Blank PAN entry in OrderDetail can be deleted')
            error_message = f"No. of Blank PAN Entry: {orderdetail}"
            messages.error(request, error_message)
        elif var == 3:
            messages.error(
            request, 'Order Not Modified')
        else:        
            messages.success(
            request, 'Order Modified successfully')
        
    return redirect(f"/{IPOid}/Order/{Grpf}/{OrCtf}/{InTyf}?page={page_number}")    

#change rate fun 
@allowed_users(allowed_roles=['Broker'])
def EditOrderRate(request, IPOid, OrderId, GrpName, OrderCategory, InvestorType):
    userid = request.user
    if request.method == "POST":
        Rate = request.POST.get('Rate', '')
        order = Order.objects.get(user=request.user, id=OrderId)
        order.Rate = Rate
        order.save()
        calculate(IPOid,request.user,OrderId)
        messages.success(request, 'Order Modified successfully')
    return redirect(f"/{IPOid}/Order/{GrpName}/{OrderCategory}/{InvestorType}")

@allowed_users(allowed_roles=['Broker'])
def SetRate(request, IPOid):
    IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)
    try:
        query = RateList.objects.get(
            RateListIPOName=IPOName, user=request.user)
    except:
        query = 0

    if request.method == "POST":
        IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)
        query = RateList.objects.filter(
            RateListIPOName=IPOName, user=request.user)
        KostakRate = request.POST.get('KostakRate', '')
        KostakSellRate = request.POST.get('KostakSellRate', '')
        SubjectToRate = request.POST.get('SubjectToRate', '')
        SubjectToSellRate = request.POST.get('SubjectToSellRate', '')
        PremiumRate = request.POST.get('PremiumRate', '')
        KostakQTY = request.POST.get('KostakQTY', '')
        KostakSellQTY = request.POST.get('KostakSellQTY', '')
        SubjectToQTY = request.POST.get('SubjectToQTY', '')
        SubjectToSellQTY = request.POST.get('SubjectToSellQTY', '')
        PremiumQTY = request.POST.get('PremiumQTY', '')
        PremiumSellQTY = request.POST.get('PremiumSellQTY', '')
        PremiumSellRate = request.POST.get('PremiumSellRate', '')
        if query.exists():
            query1 = RateList.objects.get(
                RateListIPOName=IPOName, user=request.user)
            if KostakQTY != '':
                query1.kostakBuyRate = KostakRate
                query1.KostakBuyQty = KostakQTY
                query1.save()
            if KostakSellQTY != '':
                query1.kostakSellRate = KostakSellRate
                query1.KostakSellQty = KostakSellQTY
                query1.save()
            if SubjectToQTY != '':
                query1.SubjecToBuyRate = SubjectToRate
                query1.SubjecToBuyQty = SubjectToQTY
                query1.save()
            if SubjectToSellQTY != '':
                query1.SubjecToSellRate = SubjectToSellRate
                query1.SubjecToSellQty = SubjectToSellQTY
                query1.save()
            if PremiumQTY != '':
                query1.PremiumBuyRate = PremiumRate
                query1.PremiumBuyQty = PremiumQTY
                query1.save()
            if PremiumSellQTY != '':
                query1.PremiumSellRate = PremiumSellRate
                query1.PremiumSellQty = PremiumSellQTY
                query1.save()
        else:
            if KostakQTY == '':
                KostakQTY = 0
            if KostakSellQTY == '':
                KostakSellQTY = 0
            if SubjectToQTY == '':
                SubjectToQTY = 0
            if SubjectToSellQTY == '':
                SubjectToSellQTY = 0
            if PremiumQTY == '':
                PremiumQTY = 0
            if PremiumSellQTY == '':
                PremiumSellQTY = 0
            ratelist = RateList(user=request.user, RateListIPOName=IPOName, kostakBuyRate=KostakRate, KostakBuyQty=KostakQTY,
                                SubjecToBuyRate=SubjectToRate, SubjecToBuyQty=SubjectToQTY, PremiumBuyRate=PremiumRate, PremiumBuyQty=PremiumQTY, PremiumSellRate=PremiumSellRate, PremiumSellQty=PremiumSellQTY)
            ratelist.save()
        return redirect("/")
    return render(request, 'SetRate.html', {'Ratelist': query, 'IPOName': IPOName,'IPOid':IPOid})

def is_valid_queryparam(param):
    return param != '' and param is not None

def get_rates_json(request, IPOid, Ordtyp):
    group = request.GET.get('group', 'All')
    category = request.GET.get('category', 'All')
    investor = request.GET.get('investor', 'All')
    order_date = request.GET.get('date', 'None')
    order_time = request.GET.get('time', 'None')
    
    group = unquote(group)
    category = unquote(category)
    investor = unquote(investor)
    
    has_session_access = request.session.get(f'access_auth_{IPOid}', False)
    if has_session_access:
        user = request.session[f'link_owner_{IPOid}']
        entry = OrderDetail.objects.filter(user=user, Order__OrderIPOName_id=IPOid, Order__OrderType=Ordtyp)
    else:
        if not request.user.is_authenticated:
            return JsonResponse({'rates': []})
        if request.user.groups.all()[0].name == 'Broker':
            entry = OrderDetail.objects.filter(user=request.user, Order__OrderIPOName_id=IPOid, Order__OrderType=Ordtyp)
        else:
             entry = OrderDetail.objects.filter(user=request.user.Broker_id, Order__OrderIPOName_id=IPOid, Order__OrderGroup_id=request.user.Group_id, Order__OrderType=Ordtyp)

    # Apply Date/Time filters if present
    if order_date != 'None' and is_valid_queryparam(order_date):
        fmt_date = order_date[0:4] +'-'+ order_date[4:6]+'-'+ order_date[6:8]
        entry = entry.filter(Order__OrderDate=fmt_date)
    if order_time != 'None' and is_valid_queryparam(order_time):
        fmt_time = order_time[0:2] + ':' + order_time[2:4] + ':' + order_time[4:6]
        entry = entry.filter(Order__OrderTime=fmt_time)

    if is_valid_queryparam(group) and group != 'All':
        entry = entry.filter(Order__OrderGroup__GroupName=group)
    if is_valid_queryparam(category) and category != 'All':
        entry = entry.filter(Order__OrderCategory=category)
    if is_valid_queryparam(investor) and investor != 'All':
        entry = entry.filter(Order__InvestorType=investor)
        
    rates = list(entry.values_list('Order__Rate', flat=True).distinct().order_by('Order__Rate'))
    return JsonResponse({'rates': rates})


#app-buy & app-sell oder details fun
# @allowed_users(allowed_roles=['Broker', 'Customer'])
def OrderDetailFunction(request, IPOid, Ordtyp, GrpName=None, OrderCategory=None, InvestorType=None, OrderDate=None, OrderTime=None,Rate='All'):
    has_session_access = request.session.get(f'access_auth_{IPOid}', False)
    if not request.user.is_authenticated and not has_session_access:
        return redirect('login') # Block unauthorized people
    
    if has_session_access:
        user = request.session[f'link_owner_{IPOid}']
        link_id = request.session[f'access']
        Group_id = SharedLink.objects.get(id=link_id).group
        entry = OrderDetail.objects.filter(
            user=user, Order__OrderIPOName_id=IPOid, Order__OrderType=Ordtyp)
        Group = GroupDetail.objects.filter(
            user=user,GroupName=Group_id)
        IPOName = CurrentIpoName.objects.get(id=IPOid, user=user)
        
    else:
        if request.user.groups.all()[0].name == 'Broker':
            entry = OrderDetail.objects.filter(
                user=request.user, Order__OrderIPOName_id=IPOid, Order__OrderType=Ordtyp)
            Group = GroupDetail.objects.filter(
                user=request.user)
            IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)
        else:
            entry = OrderDetail.objects.filter(
                user=request.user.Broker_id, Order__OrderIPOName_id=IPOid, Order__OrderGroup_id=request.user.Group_id, Order__OrderType=Ordtyp, Order__InvestorType=InvestorType)
            Group = GroupDetail.objects.filter(
                user=request.user.Broker_id, id=request.user.Group_id)
            
            IPOName = CurrentIpoName.objects.get(
                id=IPOid, user=request.user.Broker_id)
        
    group_names_list = []
    Panding_Pan_GroupList = []
    
    entry_for_gp = entry.select_related('OrderDetailPANNo__Group', 'Order__OrderGroup')
    for order_detail_entry in entry_for_gp:
        if order_detail_entry.OrderDetailPANNo:  # Check if OrderDetailPANNo is not null
            group_name = order_detail_entry.OrderDetailPANNo.Group.GroupName
            Group_emial = order_detail_entry.OrderDetailPANNo.Group.Email
        else:
            group_name = order_detail_entry.Order.OrderGroup.GroupName
            Group_emial = order_detail_entry.Order.OrderGroup.Email
            if not any(g['group_name'] == group_name for g in Panding_Pan_GroupList):
                Panding_Pan_GroupList.append({'group_name':group_name,'Group_emial':Group_emial})
        
        if not any(g['group_name'] == group_name for g in group_names_list):
            group_names_list.append({'group_name':group_name,'Group_emial':Group_emial})
        
    # unique_rates = entry.values_list('Order__Rate', flat=True).distinct().order_by('Order__Rate')z
    RateFilterValue = Rate
    Od_time = OrderTime
    Od_Date = OrderDate
    if OrderDate == "None":
        OrderDate = None

    if OrderTime == "None":
        OrderTime = None 

    if OrderDate != None:
        OrderDate = OrderDate[0:4] +'-'+ OrderDate[4:6]+'-'+ OrderDate[6:8]
        entry = entry.filter(Order__OrderDate = OrderDate)        

    if OrderTime != None:
        OrderTime = OrderTime[0:2] + ':' + OrderTime[2:4] + ':' + OrderTime[4:6]
        entry = entry.filter(Order__OrderTime = OrderTime)

    AppTotal=len(entry)
    Appwithoutpan=len(entry.filter(OrderDetailPANNo_id=None))
    
    unique_rates = entry.values_list('Order__Rate', flat=True).distinct().order_by('Order__Rate')

    # if GrpName == None and OrderCategory == None and InvestorType == None:
    #     Groupfilter = 'All'
    #     IPOTypefilter = 'All'
    #     InvestorTypeFilter = 'All'
        
    #     if IPOTypefilter == 'All' and Groupfilter=='All' and InvestorTypeFilter=="All":
    #         pass
    #     elif IPOTypefilter == 'All' and  Groupfilter=='All':
    #         entry =  entry.filter(Order__InvestorType=InvestorTypeFilter)
    #     elif IPOTypefilter == 'All' and InvestorTypeFilter=='All':   
    #         entry = entry.filter(Order__OrderGroup__GroupName=Groupfilter)
    #     elif InvestorTypeFilter=='All' and  Groupfilter=='All':
    #         entry =  entry.filter(Order__OrderCategory=IPOTypefilter)
    #     elif IPOTypefilter == 'All':   
    #         entry = entry.filter(Order__OrderGroup__GroupName=Groupfilter, Order__InvestorType=InvestorTypeFilter)
    #     elif Groupfilter=='All':
    #         entry =  entry.filter(Order__OrderCategory=IPOTypefilter, Order__InvestorType=InvestorTypeFilter)
    #     elif InvestorTypeFilter=='All':
    #         entry =  entry.filter(Order__OrderCategory=IPOTypefilter, Order__OrderGroup__GroupName=Groupfilter)
    #     else:
    #         entry =  entry.filter(Order__OrderCategory=IPOTypefilter, Order__OrderGroup__GroupName=Groupfilter,Order__InvestorType=InvestorTypeFilter)
    #     AppTotal=len(entry)
    #     Appwithoutpan=len(entry.filter(OrderDetailPANNo_id=None))
    
    # else:
    #     Groupfilter = unquote(GrpName)
    #     IPOTypefilter = unquote(OrderCategory)
    #     InvestorTypeFilter = InvestorType

    #     if IPOTypefilter == 'All' and Groupfilter=='All' and InvestorTypeFilter=="All":
    #         pass
    #     elif IPOTypefilter == 'All' and  Groupfilter=='All':
    #         entry =  entry.filter(Order__InvestorType=InvestorTypeFilter)
    #     elif IPOTypefilter == 'All' and InvestorTypeFilter=='All':   
    #         entry = entry.filter(Order__OrderGroup__GroupName=Groupfilter)
    #     elif InvestorTypeFilter=='All' and  Groupfilter=='All':
    #         entry =  entry.filter(Order__OrderCategory=IPOTypefilter)
    #     elif IPOTypefilter == 'All':   
    #         entry = entry.filter(Order__OrderGroup__GroupName=Groupfilter, Order__InvestorType=InvestorTypeFilter)
    #     elif Groupfilter=='All':
    #         entry =  entry.filter(Order__OrderCategory=IPOTypefilter, Order__InvestorType=InvestorTypeFilter)
    #     elif InvestorTypeFilter=='All':
    #         entry =  entry.filter(Order__OrderCategory=IPOTypefilter, Order__OrderGroup__GroupName=Groupfilter)
    #     else:
    #         entry =  entry.filter(Order__OrderCategory=IPOTypefilter, Order__OrderGroup__GroupName=Groupfilter,Order__InvestorType=InvestorTypeFilter)
    #     AppTotal=len(entry)
    #     Appwithoutpan=len(entry.filter(OrderDetailPANNo_id=None))
    
    if GrpName is None and OrderCategory is None and InvestorType is None:
        Groupfilter = 'All'
        IPOTypefilter = 'All'
        InvestorTypeFilter = 'All'
    else:
        Groupfilter = unquote(GrpName)
        IPOTypefilter = unquote(OrderCategory)
        InvestorTypeFilter = InvestorType

    # ---- Rate Normalize ----
    if RateFilterValue == "None" or RateFilterValue is None:
        RateFilterValue = 'All'
    elif RateFilterValue != 'All':
        RateFilterValue = float(RateFilterValue)
    else:
        RateFilterValue = RateFilterValue

    # ---- Apply Filters ----
    filters = {}

    if IPOTypefilter != 'All':
        filters['Order__OrderCategory'] = IPOTypefilter

    if Groupfilter != 'All':
        filters['Order__OrderGroup__GroupName'] = Groupfilter

    if InvestorTypeFilter != 'All':
        filters['Order__InvestorType'] = InvestorTypeFilter

    if RateFilterValue != 'All':
        filters['Order__Rate'] = float(RateFilterValue)

    entry = entry.filter(**filters)

    # ---- Counts ----
    AppTotal = len(entry)
    Appwithoutpan = len(entry.filter(OrderDetailPANNo_id=None))

    if request.method == "POST":
        if has_session_access:
            user = request.session[f'link_owner_{IPOid}']
            entry = OrderDetail.objects.filter(
                    user=user, Order__OrderIPOName_id=IPOid, Order__OrderType=Ordtyp)
            Groupfilter = unquote(GrpName)
        else:
            if request.user.groups.all()[0].name == 'Broker':
                entry = OrderDetail.objects.filter(
                    user=request.user, Order__OrderIPOName_id=IPOid, Order__OrderType=Ordtyp)
            else:
                entry = OrderDetail.objects.filter(
                    user=request.user.Broker_id, Order__OrderIPOName_id=IPOid, Order__OrderGroup_id=request.user.Group_id, Order__OrderType=Ordtyp)
            Groupfilter = request.POST.get('Groupfilter', Groupfilter)
            RateFilterValue = request.POST.get('RateFilterValue', 'All')

        IPOTypefilter = request.POST.get('IPOTypefilter', '')
        InvestorTypeFilter = request.POST.get('InvestorTypeFilter', '')
        if Groupfilter == '' or Groupfilter == None:
            Groupfilter = 'All'
        if IPOTypefilter == '' or IPOTypefilter == None:
            IPOTypefilter = 'All'
        if InvestorTypeFilter == '' or InvestorTypeFilter == None:
            InvestorTypeFilter = 'All'
        if RateFilterValue == '' or RateFilterValue == None:
            RateFilterValue = 'All'

        unique_rates = entry.values_list('Order__Rate', flat=True).distinct().order_by('Order__Rate')
        
        if is_valid_queryparam(Groupfilter) and Groupfilter != 'All':
            entry = entry.filter(Order__OrderGroup__GroupName=Groupfilter)
        if is_valid_queryparam(IPOTypefilter) and IPOTypefilter != 'All':
            entry = entry.filter(Order__OrderCategory=IPOTypefilter)
        if is_valid_queryparam(InvestorTypeFilter) and InvestorTypeFilter != 'All':
            entry = entry.filter(Order__InvestorType=InvestorTypeFilter)
        if is_valid_queryparam(RateFilterValue) and RateFilterValue != 'All':
            entry = entry.filter(Order__Rate=float(RateFilterValue))
        
        Groupfilter = Groupfilter
        IPOTypefilter = IPOTypefilter
        InvestorTypeFilter = InvestorTypeFilter
        if RateFilterValue != 'All':
            RateFilterValue = float(RateFilterValue)
        else:
            RateFilterValue = RateFilterValue
        AppTotal=len(entry)
        Appwithoutpan=len(entry.filter(OrderDetailPANNo_id=None))

        if OrderDate != None and OrderTime!= None:
            OrderDate = OrderDate[0:4] + OrderDate[5:7] + OrderDate[8:10]
            OrderTime = OrderTime[0:2] + OrderTime[3:5] + OrderTime[6:8]
    
    page_obj = None
    try:
        page_size = request.POST.get('page_size')
        if page_size != '' and page_size != None:
            request.session['page_size'] = page_size
        else:
            page_size = 50
    except:
        page_size = 50
        
    Data = []
    if has_session_access:
        user = request.session[f'link_owner_{IPOid}']
        entry = (
                entry
                .select_related("Order", "Order__OrderGroup", "OrderDetailPANNo", "OrderDetailPANNo__Group")
                .filter(user=user, Order__OrderIPOName_id=IPOid, Order__OrderType=Ordtyp)
                .order_by("Order__OrderGroup__GroupName", "-Order__OrderDate", "-Order__OrderTime", "-id")
            )
    else:
        if request.user.groups.all()[0].name == 'Broker':
            entry = (
                entry
                .select_related("Order", "Order__OrderGroup", "OrderDetailPANNo", "OrderDetailPANNo__Group")
                .filter(user=request.user, Order__OrderIPOName_id=IPOid, Order__OrderType=Ordtyp)
                .order_by("Order__OrderGroup__GroupName", "-Order__OrderDate", "-Order__OrderTime", "-id")
            )
        else:
            entry = (
                entry
                .select_related("Order", "Order__OrderGroup", "OrderDetailPANNo", "OrderDetailPANNo__Group")
                .filter(user=request.user.Broker_id, Order__OrderIPOName_id=IPOid, Order__OrderGroup_id=request.user.Group_id, Order__OrderType=Ordtyp)
                .order_by("Order__OrderGroup__GroupName", "-Order__OrderDate", "-Order__OrderTime", "-id")
            )

    ordering = [
        "OrderDetailPANNo",      # This handles the "blank" requirement
        "Order__OrderGroup__GroupName", 
        "-Order__OrderDate", 
        "-Order__OrderTime", 
        "-id"
    ]
    entry = entry.order_by(*ordering)
    if entry is not None and entry.exists():
        if page_size == 'All':
            paginator = Paginator(entry,len(entry))
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
        else:
            paginator = Paginator(entry, page_size)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
        start_index = (page_obj.number - 1) * page_obj.paginator.per_page
        Data = []
        for i, order_detail in enumerate(page_obj, start=start_index + 1):
            pan = order_detail.OrderDetailPANNo  # cached from select_related
            order = order_detail.Order           # cached from select_related
            group = order.OrderGroup             # cached
            
            Data.append({
                'id': order_detail.id,
                'sr_no': i,
                'OrderGroup': group.GroupName if group else '',
                'OrderCategory': order.OrderCategory,
                'OrderType': order.OrderType,
                'InvestorType': order.InvestorType,
                'Rate': order.Rate,
                'PANNo': pan.PANNo if pan else '',
                'Name': pan.Name if pan else '',
                'Client_id': pan.id if pan else '',
                'client_Name': pan.Name if pan else '',
                'AllotedQty': float(order_detail.AllotedQty) if order_detail.AllotedQty is not None else '',
                'Alloted_qty': float(order_detail.AllotedQty) if order_detail.AllotedQty is not None else '',
                'DematNumber': order_detail.DematNumber or '',
                'Demate_number': order_detail.DematNumber or '',
                'ApplicationNumber': order_detail.ApplicationNumber or '',
                'Application_Number': order_detail.ApplicationNumber or '',
                'Remark': format_remark(order.remark) or "-",
                'Date': order.OrderDate,
                'Time': order.OrderTime,
            })

    else:
        paginator = Paginator([], 1)
        page_obj = paginator.get_page(1)
    
    df = pd.DataFrame.from_records(Data)
    
    # html_table = "<table>\n"
    html_table = "<thead><tr style='text-align: center;'>"
    html_table += "<th data-sort='number'><input type='checkbox' id='select_all_rows' onclick='toggleAllRows(this)'> Sr No.</th>"
    html_table += "<th data-sort='string'>Group</th>"
    html_table += "<th data-sort='string'>Order Category</th>"
    if IPOName.IPOType == "MAINBOARD":
        html_table += "<th data-sort='string'>Investor Type</th>"
    html_table += "<th data-sort='number'>Rate</th>"
    html_table += "<th data-sort='input'>PAN No<span style='color: red;'>*</span></th>"
    html_table += "<th data-sort='input'>Client Name</th>"
    html_table += "<th data-sort='input'>Alloted Qty</th>"
    html_table += "<th data-sort='input'>Demat No</th>"
    html_table += "<th data-sort='input'>Application No</th>"
    html_sort_type = "datetime"
    html_table += f"<th data-sort='{html_sort_type}'>Date and Time</th>"
    html_table += "<th data-sort='string'>Remark</th>"
    html_table += "</tr></thead>\n"
    
    html_table += "<tbody style='text-align: center;white-space: nowrap;'>"
    if df.empty:
        column_count = 11 if IPOName.IPOType == "MAINBOARD" else 10
        html_table += f"<tr class='odd'><td colspan='{column_count}' valign='top' class='dataTables_empty'>No data available</td></tr>"
    else:
        for i, row in df.iterrows():
            datetime_str  = f"{row.Date} {row.Time}"
            datetime_obj = datetime.strptime(datetime_str , "%Y-%m-%d %H:%M:%S")
            formatted_datetime = datetime_obj.strftime("%b. %d, %Y %I:%M %p")
            html_table += f"<td><input type='checkbox' class='row_checkbox' data-row-id='{row.id}'> {row.sr_no}</td>"
            if request.user.is_authenticated:
                html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','{row.OrderGroup}','All','All','{Ordtyp}')\" title=\"Double-click to filter by this Group\">{row.OrderGroup}</td>"
                html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','All','{row.OrderCategory}','All','{Ordtyp}')\" title=\"Double-click to filter by this Group\">{row.OrderCategory}</td>"
                if IPOName.IPOType == 'MAINBOARD':
                    html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','All','All','{row.InvestorType}','{Ordtyp}')\" title=\"Double-click to filter by this Group\">{row.InvestorType}</td>"
            else:
                html_table += f"<td>{row.OrderGroup}</td>"
                html_table += f"<td >{row.OrderCategory}</td>"
                if IPOName.IPOType == 'MAINBOARD':
                    html_table += f"<td >{row.InvestorType}</td>"
            html_table += f"<td>{row.Rate}</td>"
            if Ordtyp == 'BUY' or request.user.is_authenticated:
                html_table += f"<td style='width:185px;'><input class='auto' type='text' style='text-transform: uppercase;  width:165px;' maxlength='10' minlength='10' name='PAN_{row.id}_{row.Rate}_{row.Client_id}_{row.Alloted_qty}_{row.Demate_number}_{row.Application_Number}_{row.client_Name}' id='PAN_{ row.id }' onclick='functiontest({row.id})' value='{row.PANNo}' onfocus='hideTooltip({ row.id })' onblur='checkPAN({ row.id })'><div id='tooltip_{ row.id }' class='Shadow1' style='display:none;'>Invalid PAN number</div></td>"
                html_table += f"<td style='width:185px;'><input class='auto1' type='text' style='width:165px;' name='clientname_{row.id}' value='{row.Name}' id='clientname_{row.id}' oninput='sanitizeInput(this)' onblur='checkValidChars(this, \"tooltip_app_{row.id}\")' ><div id='clientname_tooltip_{row.id}' class='Shadow1' style='display:none; color:red; font-size:12px;'>Only letters, numbers, and . - & / @ _ are allowed</div></td>"
            else:
                html_table += f"<td style='width:185px;'><input class='auto' type='text' disabled style='text-transform: uppercase;  width:165px; cursor: not-allowed;' maxlength='10' minlength='10' name='PAN_{row.id}_{row.Rate}_{row.Client_id}_{row.Alloted_qty}_{row.Demate_number}_{row.Application_Number}_{row.client_Name}' id='PAN_{ row.id }' onclick='functiontest({row.id})' value='{row.PANNo}' onfocus='hideTooltip({ row.id })' onblur='checkPAN({ row.id })'><div id='tooltip_{ row.id }' class='Shadow1' style='display:none;'>Invalid PAN number</div></td>"
                html_table += f"<td style='width:185px;'><input class='auto1' type='text' disabled style='width:165px; cursor: not-allowed;' name='clientname_{row.id}' value='{row.Name}' id='clientname_{row.id}' oninput='sanitizeInput(this)' onblur='checkValidChars(this, \"tooltip_app_{row.id}\")' ><div id='clientname_tooltip_{row.id}' class='Shadow1' style='display:none; color:red; font-size:12px;'>Only letters, numbers, and . - & / @ _ are allowed</div></td>"
                
            if request.user.is_authenticated:
                if row.AllotedQty != '':
                    html_table += f"<td style='width:90px;'><input type='text' onkeypress='return event.charCode >= 48 && event.charCode <= 57 || event.charCode == 46' style='width: 55px;' name='allotedqty_{row.id}' value='{int(row.AllotedQty) if row.AllotedQty.is_integer() else row.AllotedQty}'></td>"
                else:
                    html_table += f"<td style='width:90px;'><input type='text' onkeypress='return event.charCode >= 48 && event.charCode <= 57 || event.charCode == 46' style='width: 55px;' name='allotedqty_{row.id}' value=''></td>"
            else:
                # UNAUTHORIZED: Show plain text only (No input tag exists to be hacked)
                if row.AllotedQty != '':
                    val = int(row.AllotedQty) if row.AllotedQty.is_integer() else row.AllotedQty
                    # html_table += f"<td style='width:90px;'><input type='text' disabled style='width: 55px; cursor: not-allowed; pointer-events: none;' name='allotedqty_{row.id}' value='{val}'></td>"
                    html_table += f""" <td style='width:90px;'>
                        <input type='text' disabled style='width: 55px; cursor: not-allowed;' value='{val}'>
                        <input type='hidden' name='allotedqty_{row.id}' value='{val}'>
                    </td>"""
                else:
                    # val = int(row.AllotedQty) if row.AllotedQty.is_integer() else row.AllotedQty
                    html_table += f""" <td style='width:90px;'>
                        <input type='text' disabled style='width: 55px; cursor: not-allowed;' value=''>
                        <input type='hidden' name='allotedqty_{row.id}' value=''>
                    </td>"""
                    # html_table += f"<td style='width:90px;'><input type='text' disabled style='width: 55px; cursor: not-allowed; pointer-events: none;' name='allotedqty_{row.id}' value=''></td>"
            
            if Ordtyp == 'BUY' or request.user.is_authenticated:
                html_table += f"<td style='width:185px;'><input type='text' style='width:165px;' name='DematNo_{row.id}' oninput='sanitizeInput(this)' onblur='checkValidChars(this, \"tooltip_app_{row.id}\")'  value='{row.DematNumber}'></td>"
                html_table += f"<td style='width:185px;'><input type='text' style='width:165px;' name='Application_{row.id}' oninput='sanitizeInput(this)' onblur='checkValidChars(this, \"tooltip_app_{row.id}\")' value='{row.ApplicationNumber}'></td>"
            else:
                html_table += f"<td style='width:185px;'><input type='text' disabled style='width:165px; cursor: not-allowed;' name='DematNo_{row.id}' oninput='sanitizeInput(this)' onblur='checkValidChars(this, \"tooltip_app_{row.id}\")'  value='{row.DematNumber}'></td>"
                html_table += f"<td style='width:185px;'><input type='text' disabled style='width:165px; cursor: not-allowed;' name='Application_{row.id}' oninput='sanitizeInput(this)' onblur='checkValidChars(this, \"tooltip_app_{row.id}\")' value='{row.ApplicationNumber}'></td>"
            html_table += f"<td>{formatted_datetime}</td>"
            safe_remark = row.Remark.replace("'", "\\'").replace('"', '&quot;') if row.Remark else ""
            html_table += f"<td style='white-space: nowrap; max-width: 300px; overflow: hidden; text-overflow: ellipsis; cursor: pointer; outline: none;' tabindex='0' onclick=\"this.style.whiteSpace=this.style.whiteSpace==='normal'?'nowrap':'normal'\" onblur=\"this.style.whiteSpace='nowrap'\" title='{safe_remark}'>{row.Remark}</td>"
            html_table += "</tr>\n"
        
    html_table += "</tbody>"    
    # html_table += "</table>"    
    
    if not has_session_access:
        PRI_limit  = CustomUser.objects.get(username = request.user)
        is_premium_user = PRI_limit.Allotment_access    
        
        is_customer = request.user.groups.filter(name='Customer').exists()
    else:
        is_customer = False
        is_premium_user = False
        
    recevied_pan = AppTotal - Appwithoutpan
    
    # Pre-fetch existing PANs for this IPO and OrderType to enable frontend duplicate validation
    if has_session_access:
        owner = request.session[f'link_owner_{IPOid}']
    else:
        owner = request.user if request.user.groups.filter(name='Broker').exists() else request.user.Broker_id
        
    # Map PAN -> [list of row IDs it belongs to] for proper deduplication on frontend
    existing_pans_data = OrderDetail.objects.filter(
        user=owner, 
        Order__OrderIPOName_id=IPOid, 
        Order__OrderType=Ordtyp
    ).exclude(OrderDetailPANNo=None).values('OrderDetailPANNo__PANNo', 'id')
    
    existing_pans = {}
    for ep in existing_pans_data:
        p = ep['OrderDetailPANNo__PANNo'].upper().strip()
        rid = ep['id']
        if p not in existing_pans:
            existing_pans[p] = []
        existing_pans[p].append(rid)
    if(Ordtyp == 'BUY'):
        return render(request, 'OrderDetail.html', {'existing_pans': json.dumps(existing_pans),"recevied_pan":recevied_pan,'is_customer': is_customer,'is_premium_user': str(is_premium_user),'html_table': html_table, 'unique_rates':unique_rates, 'RateFilterValue':RateFilterValue, 'Groupfilter': Groupfilter, 'IPOTypefilter': IPOTypefilter,'group_names_list':json.dumps(group_names_list),'Panding_Pan_GroupList':json.dumps(Panding_Pan_GroupList), 'InvestorTypeFilter':InvestorTypeFilter, 'IPOName': IPOName, 'Group': Group.order_by('GroupName'), 'IPOid': IPOid, 'AppTotal':AppTotal,'Appwithoutpan':Appwithoutpan,'OrderDate': Od_Date, 'OrderTime': Od_time, 'page_obj': page_obj,'page_size':page_size })
    else:
        return render(request, 'OrderDetail - Sell.html', {'existing_pans': json.dumps(existing_pans),"recevied_pan":recevied_pan,'is_customer': is_customer,'is_premium_user': str(is_premium_user),'html_table': html_table, 'unique_rates':unique_rates, 'RateFilterValue':RateFilterValue, 'Groupfilter': Groupfilter, 'IPOTypefilter': IPOTypefilter, 'InvestorTypeFilter':InvestorTypeFilter,'group_names_list':json.dumps(group_names_list),'Panding_Pan_GroupList':json.dumps(Panding_Pan_GroupList), 'IPOName': IPOName, 'Group': Group.order_by('GroupName'), 'IPOid': IPOid, 'AppTotal':AppTotal,'Appwithoutpan':Appwithoutpan,'OrderDate': Od_Date, 'OrderTime': Od_time , 'page_obj': page_obj,'page_size':page_size})
    
#groupwise to move order page fun 
@allowed_users(allowed_roles=['Broker', 'Customer'])
def filterfromstatus(request, IPOid, Groupfilter, OrderCategoryFilter, InvestorTypeFilter):
    

    Groupfilter = unquote(Groupfilter) 
    OrderCategoryFilter = unquote(OrderCategoryFilter)

    if request.user.groups.all()[0].name == 'Broker':
        userid = request.user
        products = Order.objects.filter(
            user=userid, OrderIPOName_id=IPOid)
    else:
        userid = request.user.Broker_id
        products = Order.objects.filter(
            user=userid, OrderIPOName_id=IPOid, OrderGroup_id=request.user.Group_id)
    IPO = CurrentIpoName.objects.get(id=IPOid, user=userid)

    Group = GroupDetail.objects.filter(user=userid)
    if is_valid_queryparam(Groupfilter) and Groupfilter != 'All':
        products = products.filter(OrderGroup__GroupName=Groupfilter)
    if is_valid_queryparam(OrderCategoryFilter) and OrderCategoryFilter != 'All':
        products = products.filter(OrderCategory=OrderCategoryFilter)
    if is_valid_queryparam(InvestorTypeFilter) and InvestorTypeFilter != 'All':
        products = products.filter(InvestorType=InvestorTypeFilter)
    
    InvestorTypeFilter=InvestorTypeFilter
    Groupfilter = Groupfilter
    OrderCategoryFilter = OrderCategoryFilter
    
    if InvestorTypeFilter == '' or InvestorTypeFilter == None:
        InvestorTypeFilter = 'All'
        
    if Groupfilter == '' or Groupfilter == None:
        Groupfilter = 'All'
        
    if OrderCategoryFilter == '' or OrderCategoryFilter == None:
        OrderCategoryFilter = 'All'
    
    
    OrdCat = ['Kostak','SubjectTo','CALL','PUT']
    InvTyp = ['RETAIL','SHNI','BHNI','OPTIONS']
    OrdTyp = ['BUY','SELL']
    
    strike_dict = {}
    dict_count = {}
    dict_avg = {}
    dict_amount = {}
    
    aggregates = (
        products
        .values("OrderType", "OrderCategory", "InvestorType", "Method")
        .annotate(
            total_qty=Sum("Quantity"),
            total_amt=Sum(F("Rate") * F("Quantity")),
            total_count=Count("id")
        )
    )
    
    agg_lookup = {}
    for row in aggregates:
        key = (row["OrderCategory"], row["InvestorType"], row["OrderType"], row["Method"])
        agg_lookup[key] = {
            "count": row["total_qty"] or 0,
            "amount": row["total_amt"] or 0,
            "entries": row["total_count"] or 0,
        }

    for ordertype in OrdTyp:
        for ordercategory in OrdCat:
            for investortype in InvTyp:
                key_category = "Subject To" if ordercategory == "SubjectTo" else ordercategory
                dict_key_prefix = f"{ordercategory}{investortype}{ordertype}"

                # Lookup (we don’t hit DB here)
                # NOTE: Method could vary (Premium/Normal/Strike etc.), so we loop over methods in agg_lookup
                matching_rows = [
                    v for k, v in agg_lookup.items()
                    if k[0] == key_category and k[1] == investortype and k[2] == ordertype
                ]

                # Aggregate amounts manually (still in memory, not DB)
                total_count = sum(v["count"] for v in matching_rows)
                total_amount = 0

                for (cat, inv, ot, method), v in agg_lookup.items():
                    if cat == key_category and inv == investortype and ot == ordertype:
                        # Apply your "Subject To" premium logic here
                        if cat == "Subject To" and method == "Premium":
                            if investortype == "RETAIL":
                                lot_size = IPO.LotSizeRetail
                            elif investortype == "SHNI":
                                lot_size = IPO.LotSizeSHNI
                            elif investortype == "BHNI":
                                lot_size = IPO.LotSizeBHNI
                            else:
                                lot_size = 1
                            total_amount += (lot_size * v["amount"])
                            
                        elif investortype == "OPTIONS" and ordercategory in ["CALL", "PUT"]:
                            
                            strike = method or "NA"

                            # Initialize dict structure
                            if strike not in strike_dict:
                                strike_dict[strike] = {
                                    "CALL": {"BUY": {"count":0,"amount":0,"avg":0,"net":0},
                                            "SELL":{"count":0,"amount":0,"avg":0 ,"net":0}},
                                    "PUT":  {"BUY": {"count":0,"amount":0,"avg":0 ,"net":0},
                                            "SELL":{"count":0,"amount":0,"avg":0 ,"net":0}}
                                }
                            # Update values
                            # strike_dict[strike][ordercategory][ordertype]["count"] += v.Quantity
                            # strike_dict[strike][ordercategory][ordertype]["amount"] += (v.Rate * v.Quantity)
                            strike_dict[strike][ordercategory][ordertype]["count"] += v["count"]
                            strike_dict[strike][ordercategory][ordertype]["amount"] += v["amount"]

                            # Calculate average
                            c = strike_dict[strike][ordercategory][ordertype]["count"]
                            a = strike_dict[strike][ordercategory][ordertype]["amount"]
                            strike_dict[strike][ordercategory][ordertype]["avg"] = (a / c) if c else 0
                            
                            # Net = (BUY amount - SELL amount) for that side
                            buy_amt  = strike_dict[strike][ordercategory]["BUY"]["amount"]
                            sell_amt = strike_dict[strike][ordercategory]["SELL"]["amount"]
                            strike_dict[strike][ordercategory]["BUY"]["net"]  = buy_amt - sell_amt
                            strike_dict[strike][ordercategory]["SELL"]["net"] = sell_amt - buy_amt
                            
                            # amount = (v.Rate * v.Quantity) + amount
                            total_amount += v["amount"]
                                
                        else:
                            total_amount += v["amount"]

                # Save into dicts
                dict_count[f"{dict_key_prefix}Count"] = total_count
                dict_avg[f"{dict_key_prefix}Avg"] = (total_amount / total_count) if total_count else 0
                dict_amount[f"{dict_key_prefix}Amount"] = total_amount
    net_count = {}
    net_avg = {}
    net_amount = {}
                    
    for ordercategory in OrdCat:
        for investortype in InvTyp:
            # Keys for BUY and SELL
            buy_key_count = f"{ordercategory}{investortype}BUYCount"
            sell_key_count = f"{ordercategory}{investortype}SELLCount"
            
            buy_key_avg = f"{ordercategory}{investortype}BUYAvg"
            sell_key_avg = f"{ordercategory}{investortype}SELLAvg"

            # Get counts (default 0 if missing)
            buy_count = dict_count.get(buy_key_count, 0)
            sell_count = dict_count.get(sell_key_count, 0)
            net_c = buy_count - sell_count

            # Get amounts (Count * Avg)
            buy_amount = buy_count * dict_avg.get(buy_key_avg, 0)
            sell_amount = sell_count * dict_avg.get(sell_key_avg, 0)
            net_amt = buy_amount - sell_amount

            # Calculate net average
            if net_c != 0:
                net_a = net_amt / net_c
            else:
                net_a = 0
                
            if net_c == 0:
                net_amt = sell_amount - buy_amount

            # Store results
            key_prefix = f"{ordercategory}{investortype}Net"
            net_count[f"{key_prefix}Count"] = net_c
            net_avg[f"{key_prefix}Avg"] = round(net_a, 2)
            net_amount[f"{key_prefix}Amount"] = round(net_amt, 2)
            
    PremiumBuyfilter = products.filter(OrderType="BUY",OrderCategory="Premium")
    PremiumBuyCount11 = PremiumBuyfilter.aggregate(Sum('Quantity'))
    PremiumBuyCount1 = PremiumBuyCount11['Quantity__sum']
    if PremiumBuyCount1 == None:
        PremiumBuyCount = 0
    else:
        PremiumBuyCount = PremiumBuyCount1
    
    PremiumBuyAmount=0
    for i in PremiumBuyfilter:
        PremiumBuyAmount=(i.Quantity*i.Rate)+PremiumBuyAmount

    if PremiumBuyCount==0:
        PremiumBuyAvg=0    
    else:
        PremiumBuyAvg=PremiumBuyAmount/PremiumBuyCount
    
    PremiumSellfilter = products.filter(OrderType="SELL",OrderCategory="Premium")
    PremiumSellCount11 = PremiumSellfilter.aggregate(Sum('Quantity'))
    PremiumSellCount1 = PremiumSellCount11['Quantity__sum']
    if PremiumSellCount1 == None:
        PremiumSellCount = 0
    else:
        PremiumSellCount = PremiumSellCount1

    PremiumSellAmount=0
    for i in PremiumSellfilter:
        PremiumSellAmount=(i.Quantity*i.Rate)+PremiumSellAmount

    if PremiumSellCount==0:
        PremiumSellAvg=0    
    else:
        PremiumSellAvg=PremiumSellAmount/PremiumSellCount
    
    PremiumNetCount = PremiumBuyCount - PremiumSellCount
    Premiumavg1 = PremiumBuyCount * PremiumBuyAvg
    Premiumavg2 = PremiumSellCount * PremiumSellAvg
    pri_net_avg = Premiumavg1 - Premiumavg2
    if PremiumNetCount != 0:
        PremiumNetAvg = pri_net_avg /PremiumNetCount
    else:
        PremiumNetAvg =  0
        
    PremiumNetAmount = PremiumBuyAmount - PremiumSellAmount
    strike_prices = []
    grand_call_count = grand_call_amount = grand_put_count = grand_put_amount = 0
    for strike, cats in strike_dict.items():
        # CALL
        call_buy_count = cats["CALL"]["BUY"]["count"]
        call_sell_count = cats["CALL"]["SELL"]["count"]
        call_buy_amount = cats["CALL"]["BUY"]["amount"]
        call_sell_amount = cats["CALL"]["SELL"]["amount"]
        
        call_net_count = call_buy_count - call_sell_count
        call_avg1 = call_buy_amount - call_sell_amount
        call_avg2 = call_sell_amount - call_buy_amount
        call_net_avg = call_avg1 - call_avg2
        # call_net_amount = call_buy_amount - call_sell_amount
        if call_net_count != 0:
            call_avg = call_net_avg / call_net_count
            call_net_amount = call_buy_amount - call_sell_amount
        else:
            call_avg = 0
            call_net_amount = call_sell_amount - call_buy_amount
        # PUT
        put_buy_count = cats["PUT"]["BUY"]["count"]
        put_sell_count = cats["PUT"]["SELL"]["count"]
        put_buy_amount = cats["PUT"]["BUY"]["amount"]
        put_sell_amount = cats["PUT"]["SELL"]["amount"]

        put_net_count = put_buy_count - put_sell_count
        put_avg1 = put_buy_amount - put_sell_amount
        put_avg2 = put_sell_amount - put_buy_amount
        put_net_avg = put_avg1 - put_avg2
        # put_net_amount = put_buy_amount - put_sell_amount 
        if put_net_count != 0:
            put_avg = put_net_avg / put_net_count
            put_net_amount = put_buy_amount - put_sell_amount
        else:
            put_avg = 0 
            put_net_amount = put_sell_amount - put_buy_amount
        
        strike_prices.append({
            "value": strike,
            "call_total_count": call_net_count,
            "call_avg": (call_net_amount / call_net_count) if call_net_count else 0,
            "call_net_amount": call_net_amount,
            "put_total_count": put_net_count,
            "put_avg": (put_net_amount / put_net_count) if put_net_count else 0,
            "put_net_amount": put_net_amount,
        })
        
        grand_call_count += call_net_count
        grand_call_amount += call_net_amount
        grand_put_count += put_net_count
        grand_put_amount += put_net_amount
    grand_total = {
        "call_total_count": grand_call_count,
        "call_avg": (grand_call_amount/grand_call_count ) if grand_call_count else 0,
        "call_net_amount": grand_call_amount,
        "put_total_count": grand_put_count,
        "put_avg": grand_put_amount/grand_put_count if grand_put_count else 0,
        "put_net_amount": grand_put_amount,
    }
    
    
    category_totals = {
        "CALL": {"count": grand_call_count, "avg": grand_total["call_avg"]},
        "PUT":  {"count": grand_put_count, "avg": grand_total["put_avg"]},
    }      
    
    page_obj = None
    try:
        page_size = request.POST.get('Order_page_size')
        if page_size != '' and page_size != None:
            request.session['Order_page_size'] = page_size
        else:
            page_size = request.session['Order_page_size']
    except:
        page_size = request.session.get('Order_page_size', 50)
        
    Data=[]
    IPOName = CurrentIpoName.objects.get(id=IPOid, user=userid)
    products = products.order_by('-OrderDate','-OrderTime')
    products = products.select_related("OrderGroup")
    if page_size == 'All':
        all_rows = True
        paginator = Paginator(products,max(len(products), 1))
        page_number = request.GET.get('page','1')
        page_obj = paginator.get_page(page_number)
    else:
        paginator = Paginator(products, page_size)
        page_number = request.GET.get('page','1')
        page_obj = paginator.get_page(page_number)
    if products is not None and products.exists():
        start_index = (page_obj.number - 1) * page_obj.paginator.per_page
        
        for i,order_detail in enumerate(page_obj):
            entry_data = {
                'id':order_detail.id,
                'OrderGroup': order_detail.OrderGroup.GroupName,
                'OrderType': order_detail.OrderType,
                'OrderCategory': order_detail.OrderCategory,
                'InvestorType': order_detail.InvestorType,
                'Quantity': int(order_detail.Quantity) ,
                'Method': order_detail.Method,
                'Rate': order_detail.Rate,
                'Date':order_detail.OrderDate,
                'Time':order_detail.OrderTime,
                'Remark': format_remark(order_detail.remark) or "-",
                'sr_no': start_index + i + 1
            }
            Data.append(entry_data)
            
    df = pd.DataFrame.from_records(Data)
    html_table = "<table >\n"
    html_table = "<thead><tr class='text-center text-nowrap'>"
    html_table += "<th><input type='checkbox' id='select-all-orders' style='cursor:pointer;'> Sr No.</th>"
    html_table += "<th>Group Name</th>"
    html_table += "<th>Order Type</th>"
    html_table += "<th>Order Category</th>"
    html_table += "<th>Premium Strike Price</th>"
    if IPOName.IPOType == "MAINBOARD":
        html_table += "<th>InvestorType</th>"
    html_table += "<th> Qty</th>"
    html_table += "<th>Rate</th>"
    html_table += "<th class='skip-export'>Date and Time</th>"
    html_table += "<th class='export-only'>Date</th>"
    html_table += "<th class='export-only'>Time</th>"
    html_table += "<th class='remark-col'>Remark</th>"
    html_table += "<th class='skip-export'>Action &nbsp;</th>"
    html_table += "</tr></thead>\n"
    html_table += "<tbody class='text-center text-nowrap'>"
    for i, row in df.iterrows():
        datetime_str  = f"{row.Date} {row.Time}"
        datetime_obj = datetime.strptime(datetime_str , "%Y-%m-%d %H:%M:%S")
        formatted_datetime = datetime_obj.strftime("%b. %d, %Y | %I:%M:%S %p")
        # Export formats
        export_date = datetime_obj.strftime("%d-%m-%Y")  # DD-MM-YYYY
        export_time = datetime_obj.strftime("%H:%M:%S")  # HH:MM:SS (24 hr)
        
        html_table += "<tr style='text-align: center;'>"
        html_table += f"<td><input type='checkbox' class='order-checkbox' value='{row.id}' style='cursor:pointer;'> {row.sr_no}</td>"
        html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','{row.OrderGroup}','All','All')\" title=\"Double-click to filter by this group\">{row.OrderGroup}</td>"
        html_table += f"<td>{row.OrderType}</td>"
        html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','All','{row.OrderCategory}','All')\" title=\"Double-click to filter by this Order Category\">{row.OrderCategory}</td>"
        if row.OrderCategory != 'Premium':
            method_value = row.Method if row.Method else 'Application'
            html_table += f"<td>{method_value}</td>"
        else:
            html_table += f"<td>-</td>"
            
        if IPOName.IPOType == "MAINBOARD":
            html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','All','All','{row.InvestorType}')\" title=\"Double-click to filter by this Investor Type\">{row.InvestorType}</td>"
        if row.OrderCategory != 'Premium' and row.InvestorType != 'OPTIONS':
            html_table += f"<td><a href='/{IPOid}/OrderDetail/{row.OrderType}/{row.OrderGroup}/{ row.OrderCategory }/{row.InvestorType}/{ row.Date.strftime('%Y%m%d') }/{row.Time.strftime('%H%M%S')}{row.id}' style='color:blue; text-decoration: underline; '> {row.Quantity} </a></td>"
        else:
            html_table += f"<td>{row.Quantity }</td>"
        html_table += f"<td>{row.Rate}</td>"
        html_table += f"<td class='skip-export'>{formatted_datetime}</td>"
        html_table += f"<td class='export-only'>{export_date}</td>"
        html_table += f"<td class='export-only'>{export_time}</td>"
        safe_remark = row.Remark.replace("'", "\\'").replace('"', '&quot;') if row.Remark else ""
        html_table += f"<td style='white-space: nowrap; max-width: 300px; overflow: hidden; text-overflow: ellipsis; cursor: pointer; outline: none;' tabindex='0' onclick=\"this.style.whiteSpace=this.style.whiteSpace==='normal'?'nowrap':'normal'\" onblur=\"this.style.whiteSpace='nowrap'\" title='{safe_remark}'>{row.Remark}</td>"
        if IPOName.IPOType == "MAINBOARD":
            url = f'/{IPOid}/EditOrder/{ row.id }/{Groupfilter}/{OrderCategoryFilter}/{InvestorTypeFilter}?page={page_number}'
        else:
            InvestorTypeFilter = 'All'
            url = f'/{IPOid}/EditOrder/{ row.id }/{Groupfilter}/{OrderCategoryFilter}/{InvestorTypeFilter}?page={page_number}'
        html_table += f"<td style='white-space: nowrap;'><button onclick=\"window.location.href='{url}';\"\
                    class='btn btn-outline-primary' style='width: 72px;'>Edit</button></td>"
        
        html_table += "</tr>\n"
    html_table += "</tbody></table>"
    
    # return render(request, 'Order.html', {'Group': Group.order_by('GroupName'), 'html_table': html_table, 'IPOid': IPOid, 'IPOName': IPO, 'Groupfilter': Groupfilter,'PremiumSellAmount':PremiumSellAmount,'PremiumNetAmount':PremiumNetAmount,'PremiumBuyAmount':PremiumBuyAmount,'net_count':net_count,'net_avg':net_avg,'net_amount':net_amount  ,'OrderCategoryFilter': OrderCategoryFilter,'InvestorTypeFilter': InvestorTypeFilter, 'dict_count': dict_count, 'dict_avg': dict_avg, 'dict_amount':dict_amount, 'PremiumBuyCount':PremiumBuyCount,'PremiumSellCount':PremiumSellCount,'PremiumNetCount':PremiumNetCount,'PremiumNetAvg':PremiumNetAvg,'PremiumNetAvg':"{:.2f}".format(PremiumNetAvg),'PremiumNetCount':"{:.2f}".format(PremiumNetCount), 'PremiumSellAvg':"{:.2f}".format(PremiumSellAvg),'PremiumBuyAvg':"{:.2f}".format(PremiumBuyAvg),'page_obj': page_obj,'Order_page_size':page_size})
    return render(request, 'Order.html', {'Group': Group.order_by('GroupName'), 'html_table': html_table, 'IPOid': IPOid, 'IPOName': IPO, 'Groupfilter': Groupfilter, 'OrderCategoryFilter': OrderCategoryFilter,'category_totals': category_totals,'strike_prices': strike_prices,'grand_total': grand_total, 'InvestorTypeFilter': InvestorTypeFilter,'PremiumBuyAmount':PremiumBuyAmount,'PremiumNetAmount':PremiumNetAmount,'PremiumSellAmount':PremiumSellAmount ,'dict_count': dict_count, 'net_count':net_count ,'net_avg':net_avg ,'net_amount':net_amount ,'dict_amount':dict_amount,'dict_avg': dict_avg,'PremiumNetCount':PremiumNetCount,'PremiumNetCount':"{:.2f}".format(PremiumNetCount),'PremiumNetAvg':PremiumNetAvg,'PremiumNetAvg':"{:.2f}".format(PremiumNetAvg), 'PremiumBuyCount':PremiumBuyCount,'PremiumSellCount':PremiumSellCount,'PremiumSellAvg':"{:.2f}".format(PremiumSellAvg),'PremiumBuyAvg':"{:.2f}".format(PremiumBuyAvg),'page_obj': page_obj,'Order_page_size':page_size})

@allowed_users(allowed_roles=['Broker'])
def filterfromstatusforsubjectto(request, IPOid, Groupfilter):
    IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)
    entry = OrderDetail.objects.filter(
        user=request.user, Order__OrderIPOName_id=IPOid)
    Group = GroupDetail.objects.filter(user=request.user)
    try:
        gid = GroupDetail.objects.get(
            GroupName=Groupfilter, user=request.user).id
    except:
        pass
    IPOTypefilter = "Subject To"

    if is_valid_queryparam(Groupfilter) and Groupfilter != 'All':
        entry = entry.filter(user=request.user, Order__OrderGroup_id=gid)
    if is_valid_queryparam(IPOTypefilter) and IPOTypefilter != 'All':
        entry = entry.filter(IPOType=IPOTypefilter)
    IPOTypefilterList = {'Kostak', 'Subject To'}
    return render(request, 'OrderDetail.html', {'entry': entry, 'Groupfilter': Groupfilter, 'IPOTypefilter': IPOTypefilter, 'IPOTypefilter': IPOTypefilterList, 'IPOName': IPOName, 'Group': Group.order_by('GroupName'), 'IPOid': IPOid})

def UpdateOrderAmount(IPOid, user):
    entry = OrderDetail.objects.filter(
        user=user, Order__OrderIPOName_id=IPOid)
    order = Order.objects.filter(
        user=user, OrderIPOName_id=IPOid)
    IPOName = CurrentIpoName.objects.get(id=IPOid, user=user)
    order.update(Amount=0)
    for i in entry:
        if i.Order.OrderCategory == 'Kostak':
            if i.AllotedQty == None:
                continue
            else:
                AllotedQty = i.AllotedQty
            if i.Order.OrderType == "BUY":
                i.Order.Amount = i.Order.Amount + ((float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                                                   * float(AllotedQty)) - i.Order.Rate
            if i.Order.OrderType == "SELL":
                i.Order.Amount = i.Order.Amount + (-1*(((float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                                                        * float(AllotedQty)) - i.Order.Rate))

        if i.Order.OrderCategory == 'Subject To':
            if i.AllotedQty == None:
                continue
            else:
                AllotedQty = i.AllotedQty
            if(AllotedQty != 0):
                if i.Order.OrderType == "BUY":
                    i.Order.Amount = i.Order.Amount + ((float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                                                       * float(AllotedQty)) - i.Order.Rate
                if i.Order.OrderType == "SELL":
                    i.Order.Amount = i.Order.Amount + (-1*(((float(i.PreOpenPrice) - float(IPOName.IPOPrice))
                                                            * float(AllotedQty)) - i.Order.Rate))

            else:
                i.Order.Amount = i.Order.Amount + 0
        i.Order.save()
    for i in order:
        if i.OrderCategory == 'Premium':
            if i.OrderType == "BUY":
                i.Amount = (float(IPOName.PreOpenPrice) -
                            (float(IPOName.IPOPrice) + float(i.Rate))) * int(i.Quantity)
            if i.OrderType == "SELL":
                i.Amount = (-1*((float(IPOName.PreOpenPrice) -
                                 (float(IPOName.IPOPrice) + float(i.Rate))) * int(i.Quantity)))
            i.save()

@csrf_exempt
def update_telly_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            updateType = data.get('updateType')
            IPOId = data.get('IPO_id')
            status = data.get('status')  # This is True or False (from JS)
            try:
                if updateType == 'All':
                    Order_entry = Order.objects.filter(user=request.user,OrderIPOName=IPOId)
                    if Order_entry.exists():
                        update_kwargs = {'Telly': status}
                        if status is True or status == 'True' or status == 'true' or status == 1 or status == '1':
                            update_kwargs['tally_timestamp'] = timezone.now()
                        Order_entry.update(**update_kwargs)
                    return JsonResponse({'success': True})
                        
                else:
                    groupname = data.get('groupname')
                    Group_entry =  GroupDetail.objects.get(user=request.user,GroupName =groupname)
                    Order_entry = Order.objects.filter(user=request.user,OrderGroup= Group_entry.id,OrderIPOName=IPOId)
                    if Order_entry.exists():
                        update_kwargs = {'Telly': status}
                        if status is True or status == 'True' or status == 'true' or status == 1 or status == '1':
                            update_kwargs['tally_timestamp'] = timezone.now()
                        Order_entry.update(**update_kwargs)
                        # messages.success(request, 'Tally Status updated successfully.')
                        return JsonResponse({'success': True})
                    else:
                        # messages.error(request, 'No orders found for this group')
                        return JsonResponse({'success': False, 'error': 'No orders found for this group'})
                    # Update all entries with this group name
                    # entries = YourModel.objects.filter(user=request.user, OrderGroup=groupname)
                    # if entries.exists():
                    #     entries.update(Telly=status)
                    #     return JsonResponse({'success': True})
                    # else:
                    #     return JsonResponse({'success': False, 'error': 'No matching entries'})
            except Exception as e:
                # messages.error(request, f'Error occurred: {str(e)}')
                return JsonResponse({'success': False, 'error': str(e)})
        except Exception as e:
                # messages.error(request, f'Error occurred: {str(e)}')
                return JsonResponse({'success': False, 'error': str(e)})
        
    return JsonResponse({'success': False, 'error': 'Invalid request'})

#groupwise billing fun
@allowed_users(allowed_roles=['Broker'])
def Status(request, IPOid):
    
    IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)
    orderdetail = OrderDetail.objects.filter(
        user=request.user, Order__OrderIPOName_id=IPOid)
    order = Order.objects.filter(
        user=request.user, OrderIPOName_id=IPOid)
    Group = GroupDetail.objects.filter(user=request.user)

    page_obj = None
    try:
        page_size = request.POST.get('status_page_size')
        if page_size != '' and page_size != None:
            request.session['status_page_size'] = page_size
        else:
            page_size = request.session['status_page_size']
    except:
        page_size = request.session.get('status_page_size', 50)


    if IPOName.IPOType == "SME":      
        sme_entry_list = []     
        grpname = []
        noofapp = []
        AvgRate = []
        TotalKostak = []
        TotalAllotedKostak = []
        TotalSubjectTo = []
        TotalAllotedSubjectTo = []
        noofappsubjectto = []
        AvgRatesubjectto = []
        AvgRatepremium = []
        TtotalQtypremium = []
        TtotalAmountpremium = []
        BuyKostakApp = []
        BuyKostakAllotedApp = []
        BuyKostakAmount = []
        BuySubjectToApp = []
        BuySubjectToAllotedApp = []
        BuySubjectToAmount = []
        BuyPremiumApp = []
        BuyPremiumAmount = []
        SellKostakApp = []
        SellKostakAllotedApp = []
        SellKostakAmount = []
        SellSubjectToApp = []
        SellSubjectToAllotedApp = []
        SellSubjectToAmount = []
        SellPremiumApp = []
        SellPremiumAmount = []
        TotalAmount = []
        TotalShare = []
        TotalKostakAllotedShare = []
        TotalSubjectToAllotedShare = []
        BuyKostakAllotedShare = []
        SellKostakAllotedShare = []
        BuySubjectToAllotedShare = []
        SellSubjectToAllotedShare = []
        Group_telly_status = {}
        for GroupName in Group:
            total = 0
            totalofsubjectto = 0
            entry = order.filter(
                user=request.user, OrderGroup=GroupName)
            if len(entry)==0:
                continue
            
            sme_entry_list.append(GroupName)
        
        if page_size == 'All':
            all_rows = True
            paginator = Paginator(sme_entry_list,len(sme_entry_list))
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
        else:
            paginator = Paginator(sme_entry_list, page_size)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            
        for GroupName in page_obj:
            entry = order.filter(
                user=request.user, OrderGroup=GroupName)
            if entry.exists():
                all_true = all(str(e.Telly).lower() == 'true' or e.Telly == '1' or e.Telly == 1 for e in entry)
                latest_tally_time = entry.aggregate(Max('tally_timestamp'))['tally_timestamp__max']
                ts_str = timezone.localtime(latest_tally_time).strftime('%d-%m-%Y %H:%M:%S') if latest_tally_time else ''
                Group_telly_status[GroupName] = (all_true, ts_str)
            else:
                Group_telly_status[GroupName] = (False, '')
                
            Kostakentry = entry.filter(OrderCategory="Kostak")
            NOBUYKostak = Kostakentry.filter(OrderType="BUY")
            NOBUYKostak11 = NOBUYKostak.aggregate(Sum('Quantity'))
            NOBUYKostak1 = NOBUYKostak11['Quantity__sum']
            if NOBUYKostak1 == None:
                NOBUYKostakentry = 0
            else:
                NOBUYKostakentry = NOBUYKostak1
            NOBUYKostakentry = NOBUYKostakentry

            NOBUYKostakAllotedentry = orderdetail.filter(~Q(AllotedQty=None), ~Q(
                AllotedQty=0), Order__OrderGroup=GroupName, Order__OrderCategory="Kostak", Order__OrderType="BUY").count()

            BUYKostakentry = Kostakentry.filter(OrderType="BUY")
            BUYKostakentrytotal11 = BUYKostakentry.aggregate(Sum('Amount'))
            BUYKostakentrytotal1 = BUYKostakentrytotal11['Amount__sum']
            if BUYKostakentrytotal1 == None:
                BUYKostakentrytotal = 0
            else:
                BUYKostakentrytotal = BUYKostakentrytotal1

            NOSELLKostak = Kostakentry.filter(OrderType="SELL")
            NOSELLKostak11 = NOSELLKostak.aggregate(Sum('Quantity'))
            NOSELLKostak1 = NOSELLKostak11['Quantity__sum']
            if NOSELLKostak1 == None:
                NOSELLKostakentry = 0
            else:
                NOSELLKostakentry = NOSELLKostak1
            NOSELLKostakentry = NOSELLKostakentry
            NOSELLKostakAllotedentry = orderdetail.filter(~Q(AllotedQty=None), ~Q(
                AllotedQty=0), Order__OrderGroup=GroupName, Order__OrderCategory="Kostak", Order__OrderType="SELL").count()

            SELLKostakentry = Kostakentry.filter(OrderType="SELL")
            SELLKostakentrytotal11 = SELLKostakentry.aggregate(Sum('Amount'))
            SELLKostakentrytotal1 = SELLKostakentrytotal11['Amount__sum']
            if SELLKostakentrytotal1 == None:
                SELLKostakentrytotal = 0
            else:
                SELLKostakentrytotal = SELLKostakentrytotal1

            no = NOBUYKostakentry - NOSELLKostakentry
            total = BUYKostakentrytotal + SELLKostakentrytotal
            grpname.append(GroupName)
            noofapp.append(no)
            TotalAllotedKostakt = NOBUYKostakAllotedentry - NOSELLKostakAllotedentry
            TotalAllotedKostak.append(TotalAllotedKostakt)
            BuyKostakApp.append(NOBUYKostakentry)
            BuyKostakAllotedApp.append(NOBUYKostakAllotedentry)
            SellKostakApp.append(NOSELLKostakentry)
            SellKostakAllotedApp.append(NOSELLKostakAllotedentry)
            BuyKostakAmount.append(BUYKostakentrytotal)
            SellKostakAmount.append(SELLKostakentrytotal)
            TotalKostak.append(total)

            SubjectToentry = entry.filter(OrderCategory="Subject To")
            NOBUYSubjectTo = SubjectToentry.filter(OrderType="BUY")
            NOBUYSubjectTo11 = NOBUYSubjectTo.aggregate(Sum('Quantity'))
            NOBUYSubjectTo1 = NOBUYSubjectTo11['Quantity__sum']
            if NOBUYSubjectTo1 == None:
                NOBUYSubjectToentry = 0
            else:
                NOBUYSubjectToentry = NOBUYSubjectTo1

            NOBUYSubjectToAllotedentry = orderdetail.filter(~Q(AllotedQty=None), ~Q(
                AllotedQty=0), Order__OrderGroup=GroupName, Order__OrderCategory="Subject To", Order__OrderType="BUY").count()

            NOBUYSubjectToentry = NOBUYSubjectToentry
            BUYSubjectToentry = SubjectToentry.filter(OrderType="BUY")
            BUYSubjectToentry11 = BUYSubjectToentry.aggregate(Sum('Amount'))
            BUYSubjectToentry1 = BUYSubjectToentry11['Amount__sum']
            if BUYSubjectToentry1 == None:
                BUYSubjectToentrytotal = 0
            else:
                BUYSubjectToentrytotal = BUYSubjectToentry1

            NOSELLSubjectTo = SubjectToentry.filter(OrderType="SELL")
            NOSELLSubjectTo11 = NOSELLSubjectTo.aggregate(Sum('Quantity'))
            NOSELLSubjectTo1 = NOSELLSubjectTo11['Quantity__sum']
            if NOSELLSubjectTo1 == None:
                NOSELLSubjectToentry = 0
            else:
                NOSELLSubjectToentry = NOSELLSubjectTo1
            NOSELLSubjectToentry = NOSELLSubjectToentry

            SELLSubjectToentry = SubjectToentry.filter(OrderType="SELL")
            SELLSubjectToentry11 = SELLSubjectToentry.aggregate(Sum('Amount'))
            SELLSubjectToentry1 = SELLSubjectToentry11['Amount__sum']
            if SELLSubjectToentry1 == None:
                SELLSubjectToentrytotal = 0
            else:
                SELLSubjectToentrytotal = SELLSubjectToentry1

            NOSELLSubjectToAllotedentry = orderdetail.filter(~Q(AllotedQty=None), ~Q(
                AllotedQty=0), Order__OrderGroup=GroupName, Order__OrderCategory="Subject To", Order__OrderType="SELL").count()

            nosubjectto = NOBUYSubjectToentry - NOSELLSubjectToentry

            totalofsubjectto = BUYSubjectToentrytotal + SELLSubjectToentrytotal
            
            SubjectToAllotedShare1 = orderdetail.filter(~Q(AllotedQty=None), ~Q(AllotedQty=0), Order__OrderGroup=GroupName, Order__OrderCategory="Subject To",Order__OrderType="BUY")
            SubjectToAllotedShare11 = SubjectToAllotedShare1.aggregate(Sum('AllotedQty'))
            SubjectToAllotedShare = SubjectToAllotedShare11['AllotedQty__sum']
            if SubjectToAllotedShare == None:
                SubjectToBuyAllotedShare = 0
            else:
                SubjectToBuyAllotedShare = SubjectToAllotedShare

            KostakAllotedShare1 = orderdetail.filter(~Q(AllotedQty=None), ~Q(AllotedQty=0), Order__OrderGroup=GroupName, Order__OrderCategory="Kostak",Order__OrderType="BUY")
            KostakAllotedShare11 = KostakAllotedShare1.aggregate(Sum('AllotedQty'))
            KostakAllotedShare = KostakAllotedShare11['AllotedQty__sum']
            if KostakAllotedShare == None:
                KostakBuyAllotedShare = 0
            else:
                KostakBuyAllotedShare = KostakAllotedShare
            
            SubjectToAllotedShare1 = orderdetail.filter(~Q(AllotedQty=None), ~Q(AllotedQty=0), Order__OrderGroup=GroupName, Order__OrderCategory="Subject To",Order__OrderType="SELL")
            SubjectToAllotedShare11 = SubjectToAllotedShare1.aggregate(Sum('AllotedQty'))
            SubjectToAllotedShare = SubjectToAllotedShare11['AllotedQty__sum']
            if SubjectToAllotedShare == None:
                SubjectToSellAllotedShare = 0
            else:
                SubjectToSellAllotedShare = SubjectToAllotedShare

            KostakAllotedShare1 = orderdetail.filter(~Q(AllotedQty=None), ~Q(AllotedQty=0), Order__OrderGroup=GroupName, Order__OrderCategory="Kostak",Order__OrderType="SELL")
            KostakAllotedShare11 = KostakAllotedShare1.aggregate(Sum('AllotedQty'))
            KostakAllotedShare = KostakAllotedShare11['AllotedQty__sum']
            if KostakAllotedShare == None:
                KostakSellAllotedShare = 0
            else:
                KostakSellAllotedShare = KostakAllotedShare

            noofappsubjectto.append(nosubjectto)
            TotalAllotedSubjectTot = NOBUYSubjectToAllotedentry - NOSELLSubjectToAllotedentry
            TotalAllotedSubjectTo.append(TotalAllotedSubjectTot)
            BuySubjectToAllotedApp.append(NOBUYSubjectToAllotedentry)
            BuySubjectToApp.append(NOBUYSubjectToentry)
            SellSubjectToApp.append(NOSELLSubjectToentry)
            SellSubjectToAllotedApp.append(NOSELLSubjectToAllotedentry)
            BuySubjectToAmount.append(BUYSubjectToentrytotal)
            SellSubjectToAmount.append(SELLSubjectToentrytotal)

            TotalSubjectTo.append(totalofsubjectto)

            entry1 = order.filter(
                user=request.user, OrderGroup=GroupName, OrderCategory="Premium")
            BUYPRODUCTS = entry1.filter(OrderType="BUY")
            BAvgRate = BUYPRODUCTS.aggregate(Avg('Rate'))
            BTtotalQty = BUYPRODUCTS.aggregate(Sum('Quantity'))
            BTtotalAmount = BUYPRODUCTS.aggregate(Sum('Amount'))

            SELLPRODUCTS = entry1.filter(OrderType="SELL")
            SAvgRate = SELLPRODUCTS.aggregate(Avg('Rate'))
            STtotalQty = SELLPRODUCTS.aggregate(Sum('Quantity'))
            STtotalAmount = SELLPRODUCTS.aggregate(Sum('Amount'))
            if STtotalQty['Quantity__sum'] != None:
                STotalQty = STtotalQty['Quantity__sum']
            else:
                STotalQty = 0
            if BTtotalQty['Quantity__sum'] != None:
                BTotalQty = BTtotalQty['Quantity__sum']
            else:
                BTotalQty = 0

            TtotalQtypremiumv = BTotalQty - STotalQty
            if BTtotalAmount['Amount__sum'] != None:
                BTotalAmount = BTtotalAmount['Amount__sum']
            else:
                BTotalAmount = 0
            if STtotalAmount['Amount__sum'] != None:
                STotalAmount = STtotalAmount['Amount__sum']
            else:
                STotalAmount = 0
            TtotalAmountpremiumv = BTotalAmount + STotalAmount
            TTotalKostakAllotedShare = KostakBuyAllotedShare -KostakSellAllotedShare
            TTotalSubjectToAllotedShare = SubjectToBuyAllotedShare -SubjectToSellAllotedShare
            TTotalShare = TtotalQtypremiumv+ TTotalKostakAllotedShare+TTotalSubjectToAllotedShare
            TotalShare.append(TTotalShare)
            TotalKostakAllotedShare.append(TTotalKostakAllotedShare)
            TotalSubjectToAllotedShare.append(TTotalSubjectToAllotedShare)
            BuyKostakAllotedShare.append(KostakBuyAllotedShare)
            SellKostakAllotedShare.append(KostakSellAllotedShare)
            BuySubjectToAllotedShare.append(SubjectToBuyAllotedShare)
            SellSubjectToAllotedShare.append(SubjectToSellAllotedShare)
            TtotalQtypremium.append(TtotalQtypremiumv)
            BuyPremiumApp.append(BTotalQty)
            SellPremiumApp.append(STotalQty)
            BuyPremiumAmount.append(BTotalAmount)
            SellPremiumAmount.append(STotalAmount)
            TtotalAmountpremium.append(TtotalAmountpremiumv)

            TtotalAmount = total + totalofsubjectto + TtotalAmountpremiumv
            TotalAmount.append(TtotalAmount)
        Data = {
            'noofapp':noofapp,'TotalAllotedKostak':TotalAllotedKostak,'grpname':grpname,'BuyKostakApp':BuyKostakApp,'BuyKostakAllotedApp':BuyKostakAllotedApp,'BuyKostakAllotedShare':BuyKostakAllotedShare,'SellKostakApp':SellKostakApp,'SellKostakAllotedApp':SellKostakAllotedApp,'SellKostakAllotedShare':SellKostakAllotedShare,'BuyKostakAmount':BuyKostakAmount,'SellKostakAmount':SellKostakAmount,'noofappsubjectto':noofappsubjectto,'TotalAllotedSubjectTo':TotalAllotedSubjectTo,'BuySubjectToApp':BuySubjectToApp,'BuySubjectToAllotedApp':BuySubjectToAllotedApp,'BuySubjectToAllotedShare':BuySubjectToAllotedShare,'SellSubjectToApp':SellSubjectToApp,'SellSubjectToAllotedApp':SellSubjectToAllotedApp,'SellSubjectToAllotedShare':SellSubjectToAllotedShare,'BuySubjectToAmount':BuySubjectToAmount,'SellSubjectToAmount':SellSubjectToAmount,'TotalKostak':TotalKostak,'TotalSubjectTo':TotalSubjectTo,'TtotalQtypremium':TtotalQtypremium,'BuyPremiumApp':BuyPremiumApp,'SellPremiumApp':SellPremiumApp,'BuyPremiumAmount':BuyPremiumAmount,'SellPremiumAmount':SellPremiumAmount,'TtotalAmountpremium':TtotalAmountpremium,'TotalKostakAllotedShare':TotalKostakAllotedShare,'TotalSubjectToAllotedShare':TotalSubjectToAllotedShare,'TotalShare':TotalShare,'TotalAmount':TotalAmount
        }   
        df = pd.DataFrame.from_records(Data)
        html_table = "<table id='example' class='table table-bordered table-hover table-striped'style=\"max-width: 97vw;\">\n"
        html_table += "<thead><tr >"
        html_table += "<th rowspan='2' scope='col' class='tableline'>Tally &nbsp;</th>"
        html_table += "<th rowspan='2' scope='col' class='tableline'>Group Name &nbsp;</th>"
        html_table += "<th colspan='3'>Kostak &nbsp;</th>"
        html_table += "<th colspan='3'>Subject To &nbsp;</th>"
        html_table += "<th colspan='2'>Premium &nbsp;</th>"
        html_table += "<th rowspan='2' scope='col' class='tableline'>Total Share &nbsp;</th>"
        html_table += "<th rowspan='2' scope='col' class='tableline'>Total Amount &nbsp;</th>"
        html_table += "</tr>\n"
        html_table += "<tr>"
        # html_table += "<td></td>"
        html_table += "<td>Count</td>"
        html_table += "<td>Alloted</td>"
        html_table += "<td>Billing</td>"
        html_table += "<td>Count</td>"
        html_table += "<td>Alloted</td>"
        html_table += "<td>Billing</td>"
        html_table += "<td>Count</td>"
        html_table += "<td>Billing</td>"
        # html_table += "<td></td>"
        # html_table += "<td></td>"

        html_table += "</tr></thead>"
        float_format = "{:.0f}"
        html_table += "<tbody style='text-align: center;white-space: nowrap;'>"
        for i, row in df.iterrows():
            html_table += "<tr style='text-align: center;'>"
            is_tallied, tally_time = Group_telly_status.get(row.grpname, (False, ''))
            checked_attr = 'checked' if is_tallied else ''
            content_html = ""
            if tally_time:
                date_part, time_part = tally_time.split(" ", 1)
                prefix = "" if is_tallied else "Last: "
                content_html = f"{prefix}{date_part}<br>{time_part}"
            time_html = f"<div class='tally-time-div' style='font-size: 10px; font-weight: bold; color: #555; margin-top: 4px; line-height: 1.2;'>{content_html}</div>"
            html_table += f"<th style='text-align: center; vertical-align: e; min-width: 80px;'><div style='display: flex; flex-direction: column; align-items: center; justify-content: center;'><input type='checkbox' name='selectGroup' value='{row.grpname}' class='group-checkbox' {checked_attr} onchange='updateTellyStatus(this)'>{time_html}</div></th>"
            html_table += f"<th><a href='/{IPOid}/Order/{row.grpname}/All/All' style='color:blue; text-decoration: underline;'>{row.grpname}</a></th>"
            html_table += f"<td>"
            if row.noofapp != 0:
                html_table += f"<a style=\"color:blue; text-decoration-line: underline;\"   href=\"/{IPOid}/Order/{row.grpname}/Kostak/All\" data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY:{row.BuyKostakApp}     SELL:{row.SellKostakApp}\">"
                html_table += f"{int(row.noofapp)}</a>"
            else:
                html_table += f"{int(row.noofapp)}"
            html_table += f"</td>"
            html_table += f"<td data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY:{row.BuyKostakAllotedApp}     SELL:{row.SellKostakAllotedApp} &#013;&#010;BUY:{row.BuyKostakAllotedShare}     SELL:{row.SellKostakAllotedShare}\">{row.TotalAllotedKostak}</td>"
            html_table += f"<td data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY:{row.BuyKostakAmount}     SELL:{row.SellKostakAmount}\">{float_format.format(row.TotalKostak)}</td>"
            html_table += f"<td>"
            if row.noofappsubjectto != 0:
                html_table += f"<a style=\"color:blue; text-decoration-line: underline;\"   href=\"/{IPOid}/Order/{row.grpname}/Subject To/All\" data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY:{row.BuySubjectToApp}     SELL:{row.SellSubjectToApp}\">"
                html_table += f"{int(row.noofappsubjectto)}</a>"
            else:
                html_table += f"{int(row.noofappsubjectto)}"
            html_table += f"</td>"
            html_table += f"<td data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY:{row.BuySubjectToAllotedApp}    SELL:{row.SellSubjectToAllotedApp} &#013;&#010;BUY:{row.BuySubjectToAllotedShare}     SELL:{row.SellSubjectToAllotedShare}\">{row.TotalAllotedSubjectTo}</td>"
            html_table += f"<td data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY:{row.BuySubjectToAmount}     SELL:{row.SellSubjectToAmount}\">{float_format.format(row.TotalSubjectTo)}</td>"
            
            html_table += f"<td>"
            if row.TtotalQtypremium != 0:
                html_table += f"<a style=\"color:blue; text-decoration-line: underline;\"   href=\"/{IPOid}/Order/{row.grpname}/Premium/All\" data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY:{row.BuyPremiumApp}     SELL:{row.SellPremiumApp}\">"
                html_table += f"{int(row.TtotalQtypremium)}</a>"
            else:
                html_table += f"{int(row.TtotalQtypremium)}"
            html_table += f"</td>"
            html_table += f"<td data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY:{row.BuyPremiumAmount}     SELL:{row.SellPremiumAmount}\">{float_format.format(row.TtotalAmountpremium)}</td>"
            html_table += f"<td data-toggle=\"tooltip\" data-placement=\"auto\" title=\"Kostak:{row.TotalKostakAllotedShare}    Subject To:{row.TotalSubjectToAllotedShare}     Premium:{row.TtotalQtypremium}\">{int(row.TotalShare)}</td>"
            html_table += f"<td data-toggle=\"tooltip\" data-placement=\"auto\">{float_format.format(row.TotalAmount)}</td>"
            html_table += "</tr>\n"          
        html_table += "</tbody></table>"
                
        return render(request, 'Status.html', { 'html_table':html_table
            , "IPOName": IPOName, "IPOid": IPOid,'page_obj': page_obj,'status_page_size':page_size})
    else:
        OrderCategoryList = ['Kostak','Subject To']
        InvestorTypeList = ['RETAIL','SHNI','BHNI']
        OrderTypeList = ['BUY','SELL']
        GrpName = []
        entry_list = []

        # Kostak Variables 
        KostakRetailCount = []
        KostakRetailCountBuy = []
        KostakRetailCountSell = []

        KostakRetailAlloted = []
        KostakRetailAllotedBuy = []
        KostakRetailAllotedSell =[]  

        KostakRetailBilling = []
        KostakRetailBillingBuy = []
        KostakRetailBillingSell = []

        KostakSHNICount = []
        KostakSHNICountBuy = []
        KostakSHNICountSell = []

        KostakSHNIAlloted = []
        KostakSHNIAllotedBuy = []
        KostakSHNIAllotedSell = []

        KostakSHNIBilling = []
        KostakSHNIBillingBuy = []
        KostakSHNIBillingSell = []

        KostakBHNICount = []
        KostakBHNICountBuy = []
        KostakBHNICountSell = []

        KostakBHNIAlloted = []
        KostakBHNIAllotedBuy = []
        KostakBHNIAllotedSell = []

        KostakBHNIBilling = []
        KostakBHNIBillingBuy = []
        KostakBHNIBillingSell = []

        #SubjecTo Variables
        SubjectToRetailCount = []
        SubjectToRetailCountBuy = []
        SubjectToRetailCountSell = []

        SubjectToRetailAlloted = []
        SubjectToRetailAllotedBuy = []
        SubjectToRetailAllotedSell =[]  

        SubjectToRetailBilling = []
        SubjectToRetailBillingBuy = []
        SubjectToRetailBillingSell = []

        SubjectToSHNICount = []
        SubjectToSHNICountBuy = []
        SubjectToSHNICountSell = []

        SubjectToSHNIAlloted = []
        SubjectToSHNIAllotedBuy = []
        SubjectToSHNIAllotedSell = []

        SubjectToSHNIBilling = []
        SubjectToSHNIBillingBuy = []
        SubjectToSHNIBillingSell = []

        SubjectToBHNICount = []
        SubjectToBHNICountBuy = []
        SubjectToBHNICountSell = []

        SubjectToBHNIAlloted = []
        SubjectToBHNIAllotedBuy = []
        SubjectToBHNIAllotedSell = []

        SubjectToBHNIBilling = []
        SubjectToBHNIBillingBuy = []
        SubjectToBHNIBillingSell = []

        KostakShares = []
        SubjectToShares = []

        KostakRetailBuyShares = []
        KostakBHNIBuyShares = []
        KostakSHNIBuyShares = []

        SubjectToRetailBuyShares = [] 
        SubjectToBHNIBuyShares = []  
        SubjectToSHNIBuyShares = [] 

        KostakRetailSellShares = []  
        KostakBHNISellShares = []  
        KostakSHNISellShares = []  

        SubjectToRetailSellShares = []  
        SubjectToBHNISellShares = []  
        SubjectToSHNISellShares = []

        PremiumShares = []
        PremiumBuyShares = []
        PremiumSellShares = []
        
        PremiumBilling = []
        PremiumBuyBilling = []
        PremiumSellBilling = []
        
        CallBilling = []
        CallBuyBilling = []
        CallSellBilling = []
        
        PutBilling = []
        PutBuyBilling = []
        PutSellBilling = []

        Totalshares = []
        TotalAmount = []
        Group_telly_status = {}

        i = 0
        # for GroupName in Group:
        #     entry = order.filter(
        #         user=request.user, OrderGroup=GroupName)
        #     if len(entry)==0:
        #         continue
            
        #     entry_list.append(GroupName)
        groups_with_orders = Group.annotate(
            has_orders=Exists(
                order.filter(user=request.user, OrderGroup=OuterRef("pk"))
            )
        ).filter(has_orders=True)

        entry_list = list(groups_with_orders)
            
        if page_size == 'All':
            all_rows = True
            paginator = Paginator(entry_list,len(entry_list))
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
        else:
            paginator = Paginator(entry_list, page_size)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            
        
        # Aggregate Buy counts
        # buy_aggregates = (
        #     order
        #     .filter(OrderType="BUY")
        #     .values("OrderGroup", "OrderCategory", "InvestorType")
        #     .annotate(
        #         total_alloted=Count("id"),
        #         total_quantity=Sum("Quantity"),
        #         total_amount=Sum("Amount")
        #     )
        # )

        # # Aggregate Sell counts
        # sell_aggregates = (
        #     order
        #     .filter(OrderType="SELL")
        #     .values("OrderGroup", "OrderCategory", "InvestorType")
        #     .annotate(
        #         total_alloted=Count("id"),
        #         total_quantity=Sum("Quantity"),
        #         total_amount=Sum("Amount")
        #     )
        # )
        
        # buy_dict = {
        #     (b["OrderGroup"], b["OrderCategory"], b["InvestorType"]): b
        #     for b in buy_aggregates
        # }

        # sell_dict = {
        #     (s["OrderGroup"], s["OrderCategory"], s["InvestorType"]): s
        #     for s in sell_aggregates
        # }
        
        aggregates = (
            order
            .values("OrderGroup", "OrderCategory", "InvestorType", "OrderType")
            .annotate(
                total_quantity=Sum("Quantity"),                    
                total_amount=Sum("Amount"),
            )
        )
        aggregates2 = (
            order
            .values("OrderGroup", "OrderCategory", "InvestorType", "OrderType")
            .annotate(
        
                total_alloted=Count(
                            "orderdetail__id",  # <-- related_name used here
                            filter=Q(orderdetail__AllotedQty__isnull=False) & ~Q(orderdetail__AllotedQty=0)
                        ),
                )
            )
        
        buy_dict = {}
        sell_dict = {}

        for row in aggregates:
            key = (row["OrderGroup"], row["OrderCategory"], row["InvestorType"])
            if row["OrderType"] == "BUY":
                buy_dict[key] = row
            elif row["OrderType"] == "SELL":
                sell_dict[key] = row
                
        for row in aggregates2:
            key = (row["OrderGroup"], row["OrderCategory"], row["InvestorType"])
            if row["OrderType"] == "BUY":
                if key in buy_dict:
                    buy_dict[key]["total_alloted"] = row["total_alloted"]
                else:
                    buy_dict[key] = {"total_alloted": row["total_alloted"]}
            elif row["OrderType"] == "SELL":    
                if key in sell_dict:
                    sell_dict[key]["total_alloted"] = row["total_alloted"]
                else:
                    sell_dict[key] = {"total_alloted": row["total_alloted"]}
        
        all_sums = (
            orderdetail.filter(
                ~Q(AllotedQty=None), ~Q(AllotedQty=0),
                Order__OrderGroup__in=page_obj
            )
            .values(
                "Order__OrderGroup",
                "Order__OrderType",
                "Order__OrderCategory",
                "Order__InvestorType",
            )
            .annotate(total_qty=Sum("AllotedQty"))
        )
        
        sums_dict = {
            (
                row["Order__OrderGroup"],
                row["Order__OrderType"],
                row["Order__OrderCategory"],
                row["Order__InvestorType"],
            ): row["total_qty"] or 0
            for row in all_sums
        }
        
        all_entries = order.filter(user=request.user, OrderGroup__in=page_obj).values("OrderGroup", "Telly", "tally_timestamp")
        
        group_entries = defaultdict(list)
        for e in all_entries:
            group_entries[e["OrderGroup"]].append(e)
        
        for GroupName in page_obj:
            GrpName.append(GroupName)
            telly_values = group_entries.get(GroupName.id, [])
            if telly_values:  # group exists
                all_true = all(str(val["Telly"]).lower() == 'true' or val["Telly"] == '1' or val["Telly"] == 1 for val in telly_values)
                latest_tally_time = max((v["tally_timestamp"] for v in telly_values if v["tally_timestamp"]), default=None)
                ts_str = timezone.localtime(latest_tally_time).strftime('%d-%m-%Y %H:%M:%S') if latest_tally_time else ''
                Group_telly_status[GroupName] = (all_true, ts_str)
            else:  # no entries
                Group_telly_status[GroupName] = (False, '')

            for Ordcat in OrderCategoryList: 

                for InvTyp in InvestorTypeList:
                    key = (GroupName.id, Ordcat, InvTyp)

                    buy = buy_dict.get(key, {})
                    BuyEntryCount = buy.get("total_quantity") or 0
                    BuyAllotedCount = buy.get("total_alloted") or 0
                    BuyEntryTotal = buy.get("total_amount") or 0

                    sell = sell_dict.get(key, {})
                    SellEntryCount = sell.get("total_quantity") or 0
                    
                    SellAllotedCount = sell.get("total_alloted") or 0

                    SellEntryTotal = sell.get("total_amount") or 0
                    if SellEntryTotal == None:
                        SellEntryTotal = 0

                    EntryCount = BuyEntryCount - SellEntryCount
                    AllotedCount = BuyAllotedCount - SellAllotedCount
                    EntryTotal = BuyEntryTotal + SellEntryTotal        

                    if Ordcat == "Kostak":
                        if InvTyp == "RETAIL":
                            KostakRetailCount.append(EntryCount)
                            KostakRetailCountBuy.append(BuyEntryCount)
                            KostakRetailCountSell.append(SellEntryCount)
                            KostakRetailAlloted.append(AllotedCount)
                            KostakRetailAllotedBuy.append(BuyAllotedCount)
                            KostakRetailAllotedSell.append(SellAllotedCount)
                            KostakRetailBilling.append(EntryTotal)
                            KostakRetailBillingBuy.append(BuyEntryTotal)
                            KostakRetailBillingSell.append(SellEntryTotal)

                        elif InvTyp == "SHNI":
                            KostakSHNICount.append(EntryCount)
                            KostakSHNICountBuy.append(BuyEntryCount)
                            KostakSHNICountSell.append(SellEntryCount)
                            KostakSHNIAlloted.append(AllotedCount)
                            KostakSHNIAllotedBuy.append(BuyAllotedCount)
                            KostakSHNIAllotedSell.append(SellAllotedCount)
                            KostakSHNIBilling.append(EntryTotal)
                            KostakSHNIBillingBuy.append(BuyEntryTotal)
                            KostakSHNIBillingSell.append(SellEntryTotal)

                        else:
                            KostakBHNICount.append(EntryCount)
                            KostakBHNICountBuy.append(BuyEntryCount)
                            KostakBHNICountSell.append(SellEntryCount)
                            KostakBHNIAlloted.append(AllotedCount)
                            KostakBHNIAllotedBuy.append(BuyAllotedCount)
                            KostakBHNIAllotedSell.append(SellAllotedCount)
                            KostakBHNIBilling.append(EntryTotal)
                            KostakBHNIBillingBuy.append(BuyEntryTotal)
                            KostakBHNIBillingSell.append(SellEntryTotal)
                    else:
                        if InvTyp == "RETAIL":
                            SubjectToRetailCount.append(EntryCount)
                            SubjectToRetailCountBuy.append(BuyEntryCount)
                            SubjectToRetailCountSell.append(SellEntryCount)
                            SubjectToRetailAlloted.append(AllotedCount)
                            SubjectToRetailAllotedBuy.append(BuyAllotedCount)
                            SubjectToRetailAllotedSell.append(SellAllotedCount)
                            SubjectToRetailBilling.append(EntryTotal)
                            SubjectToRetailBillingBuy.append(BuyEntryTotal)
                            SubjectToRetailBillingSell.append(SellEntryTotal)

                        elif InvTyp == "SHNI":
                            SubjectToSHNICount.append(EntryCount)
                            SubjectToSHNICountBuy.append(BuyEntryCount)
                            SubjectToSHNICountSell.append(SellEntryCount)
                            SubjectToSHNIAlloted.append(AllotedCount)
                            SubjectToSHNIAllotedBuy.append(BuyAllotedCount)
                            SubjectToSHNIAllotedSell.append(SellAllotedCount)
                            SubjectToSHNIBilling.append(EntryTotal)
                            SubjectToSHNIBillingBuy.append(BuyEntryTotal)
                            SubjectToSHNIBillingSell.append(SellEntryTotal)

                        else:
                            SubjectToBHNICount.append(EntryCount)
                            SubjectToBHNICountBuy.append(BuyEntryCount)
                            SubjectToBHNICountSell.append(SellEntryCount)
                            SubjectToBHNIAlloted.append(AllotedCount)
                            SubjectToBHNIAllotedBuy.append(BuyAllotedCount)
                            SubjectToBHNIAllotedSell.append(SellAllotedCount)
                            SubjectToBHNIBilling.append(EntryTotal)
                            SubjectToBHNIBillingBuy.append(BuyEntryTotal)
                            SubjectToBHNIBillingSell.append(SellEntryTotal)

            key = (GroupName.id, "Premium", "PREMIUM")
            buy = buy_dict.get(key, {})
            print(buy)
            BuyPremiumShares = buy.get("total_quantity") or 0
            BuyPremiumAmount = buy.get("total_amount") or 0
            if BuyPremiumAmount == None:
                BuyPremiumAmount = 0

            sell = sell_dict.get(key, {})
            SellPremiumShares = sell.get("total_quantity") or 0
            SellPremiumAmount = sell.get("total_amount") or 0
            if SellPremiumAmount == None:
                SellPremiumAmount = 0

            PremiumSharesTotal = BuyPremiumShares - SellPremiumShares
            PremiumBillingTotal = BuyPremiumAmount + SellPremiumAmount
            
            PremiumShares.append(PremiumSharesTotal)
            PremiumBuyShares.append(BuyPremiumShares)
            PremiumSellShares.append(SellPremiumShares)
            PremiumBilling.append(PremiumBillingTotal)
            PremiumBuyBilling.append(BuyPremiumAmount)
            PremiumSellBilling.append(SellPremiumAmount)
            
            call_key = (GroupName.id, "CALL", "OPTIONS")
            
            call_buy = buy_dict.get(call_key, {})
            Call_BuyAmount = call_buy.get("total_amount") or 0
            call_sell = sell_dict.get(call_key, {})
            Call_SellAmount = call_sell.get("total_amount") or 0
                
            CallBillingTotal = Call_BuyAmount + Call_SellAmount
            CallBilling.append(CallBillingTotal)
            CallBuyBilling.append(Call_BuyAmount)
            CallSellBilling.append(Call_SellAmount)
            
            put_key = (GroupName.id, "PUT", "OPTIONS")
            put_buy = buy_dict.get(put_key, {})
            Put_BuyAmount = put_buy.get("total_amount") or 0
            put_put = sell_dict.get(put_key, {})
            Put_SellAmount = put_put.get("total_amount") or 0
            if Put_SellAmount == None:
                Put_SellAmount = 0
                
            PutBillingTotal = Put_BuyAmount + Put_SellAmount
            PutBilling.append(PutBillingTotal)
            PutBuyBilling.append(Put_BuyAmount)
            PutSellBilling.append(Put_SellAmount)
            
            
            RetailKostakBuyShares = sums_dict.get((GroupName.id, "BUY", "Kostak", "RETAIL"), 0)
            SHNIKostakBuyShares = sums_dict.get((GroupName.id, "BUY", "Kostak", "SHNI"), 0)
            BHNIKostakBuyShares = sums_dict.get((GroupName.id, "BUY", "Kostak", "BHNI"), 0)

            RetailSubjectToBuyShares = sums_dict.get((GroupName.id, "BUY", "Subject To", "RETAIL"), 0)
            SHNISubjectToBuyShares = sums_dict.get((GroupName.id, "BUY", "Subject To", "SHNI"), 0)
            BHNISubjectToBuyShares = sums_dict.get((GroupName.id, "BUY", "Subject To", "BHNI"), 0)

            RetailKostakSellShares = sums_dict.get((GroupName.id, "SELL", "Kostak", "RETAIL"), 0)
            SHNIKostakSellShares = sums_dict.get((GroupName.id, "SELL", "Kostak", "SHNI"), 0)
            BHNIKostakSellShares = sums_dict.get((GroupName.id, "SELL", "Kostak", "BHNI"), 0)

            RetailSubjectToSellShares = sums_dict.get((GroupName.id, "SELL", "Subject To", "RETAIL"), 0)
            SHNISubjectToSellShares = sums_dict.get((GroupName.id, "SELL", "Subject To", "SHNI"), 0)
            BHNISubjectToSellShares = sums_dict.get((GroupName.id, "SELL", "Subject To", "BHNI"), 0)

            KostakRetailBuyShares.append(RetailKostakBuyShares)
            KostakBHNIBuyShares.append(BHNIKostakBuyShares)
            KostakSHNIBuyShares.append(SHNIKostakBuyShares)

            SubjectToRetailBuyShares.append(RetailSubjectToBuyShares) 
            SubjectToBHNIBuyShares.append(BHNISubjectToBuyShares)  
            SubjectToSHNIBuyShares.append(SHNISubjectToBuyShares) 

            KostakRetailSellShares.append(RetailKostakSellShares)  
            KostakBHNISellShares.append(BHNIKostakSellShares)  
            KostakSHNISellShares.append(SHNIKostakSellShares)  

            SubjectToRetailSellShares.append(RetailSubjectToSellShares)  
            SubjectToBHNISellShares.append(BHNISubjectToSellShares)  
            SubjectToSHNISellShares.append(SHNISubjectToSellShares)

            TotalAmt = PremiumBillingTotal + KostakRetailBilling[i] + KostakSHNIBilling[i] + KostakBHNIBilling[i] + SubjectToRetailBilling[i] + SubjectToSHNIBilling[i] + SubjectToBHNIBilling[i] + CallBillingTotal + PutBillingTotal

            Totalshrs = RetailKostakBuyShares + BHNIKostakBuyShares + SHNIKostakBuyShares + RetailSubjectToBuyShares + BHNISubjectToBuyShares + SHNISubjectToBuyShares - (RetailKostakSellShares + BHNIKostakSellShares + SHNIKostakSellShares + RetailSubjectToSellShares + BHNISubjectToSellShares + SHNISubjectToSellShares)+PremiumSharesTotal
            
            TotalKostakShares = RetailKostakBuyShares + BHNIKostakBuyShares + SHNIKostakBuyShares - (RetailKostakSellShares + BHNIKostakSellShares + SHNIKostakSellShares)
            TotalSubjectToShares = RetailSubjectToBuyShares + BHNISubjectToBuyShares + SHNISubjectToBuyShares - (RetailSubjectToSellShares + BHNISubjectToSellShares + SHNISubjectToSellShares)

            KostakShares.append(TotalKostakShares)
            SubjectToShares.append(TotalSubjectToShares)
            Totalshares.append(Totalshrs)         
            TotalAmount.append(TotalAmt)
            i = i + 1

        Data = {
            'KostakRetailBuyShares':KostakRetailBuyShares,'KostakBHNIBuyShares':KostakBHNIBuyShares,'KostakSHNIBuyShares':KostakSHNIBuyShares,
            'SubjectToRetailBuyShares':SubjectToRetailBuyShares,'SubjectToBHNIBuyShares':SubjectToBHNIBuyShares,'SubjectToSHNIBuyShares':SubjectToSHNIBuyShares,
            'KostakRetailSellShares':KostakRetailSellShares,'KostakBHNISellShares':KostakBHNISellShares,'KostakSHNISellShares':KostakSHNISellShares,
            'SubjectToRetailSellShares':SubjectToRetailSellShares,'SubjectToBHNISellShares':SubjectToBHNISellShares,'SubjectToSHNISellShares':SubjectToSHNISellShares,
            'PremiumBuyBilling':PremiumBuyBilling,'PremiumSellBilling':PremiumSellBilling,
            'CallSellBilling':CallSellBilling,'CallBuyBilling':CallBuyBilling,'PutSellBilling':PutSellBilling,'PutBuyBilling':PutBuyBilling,
            'SubjectToBHNIAllotedSell':SubjectToBHNIAllotedSell,'SubjectToBHNIBillingBuy':SubjectToBHNIBillingBuy,'SubjectToBHNIAllotedBuy':SubjectToBHNIAllotedBuy,
            'SubjectToBHNIBillingSell':SubjectToBHNIBillingSell,'SubjectToSHNIAllotedSell':SubjectToSHNIAllotedSell,'SubjectToSHNIBillingBuy':SubjectToSHNIBillingBuy,
            'SubjectToSHNIAllotedBuy':SubjectToSHNIAllotedBuy,'SubjectToSHNIBillingSell':SubjectToSHNIBillingSell,'SubjectToRetailAllotedSell':SubjectToRetailAllotedSell,
            'SubjectToRetailBillingBuy':SubjectToRetailBillingBuy,'SubjectToRetailBillingBuy':SubjectToRetailBillingBuy,'SubjectToRetailAllotedBuy':SubjectToRetailAllotedBuy,
            'SubjectToRetailBillingSell':SubjectToRetailBillingSell,'KostakBHNIAllotedSell':KostakBHNIAllotedSell,'KostakBHNIBillingBuy':KostakBHNIBillingBuy,'KostakBHNIAllotedBuy':KostakBHNIAllotedBuy,'KostakBHNIBillingSell':KostakBHNIBillingSell,'KostakSHNIAllotedSell':KostakSHNIAllotedSell,'KostakSHNIBillingBuy':KostakSHNIBillingBuy,'KostakSHNIAllotedBuy':KostakSHNIAllotedBuy,'KostakSHNIBillingSell':KostakSHNIBillingSell,'KostakRetailAllotedSell':KostakRetailAllotedSell,'KostakRetailBillingBuy':KostakRetailBillingBuy,'KostakRetailAllotedBuy':KostakRetailAllotedBuy,'KostakRetailBillingSell':KostakRetailBillingSell,'KostakShares':KostakShares,'SubjectToShares':SubjectToShares,'PremiumBuyShares':PremiumBuyShares,'PremiumSellShares':PremiumSellShares,'SubjectToRetailCountSell':SubjectToRetailCountSell,'SubjectToSHNICountSell':SubjectToSHNICountSell,'SubjectToBHNICountSell':SubjectToBHNICountSell,'SubjectToBHNICountSell':SubjectToBHNICountSell,'SubjectToRetailCountBuy':SubjectToRetailCountBuy,'SubjectToSHNICountBuy':SubjectToSHNICountBuy,'SubjectToBHNICountBuy':SubjectToBHNICountBuy,'KostakRetailCountSell':KostakRetailCountSell,'KostakSHNICountSell':KostakSHNICountSell,'KostakBHNICountSell':KostakBHNICountSell,'KostakRetailCountBuy':KostakRetailCountBuy,'KostakSHNICountBuy':KostakSHNICountBuy,
            'KostakBHNICountBuy':KostakBHNICountBuy,'Totalshares':Totalshares,'TotalAmount':TotalAmount,'PremiumShares':PremiumShares,'PremiumBilling':PremiumBilling,'CallBilling':CallBilling,'PutBilling':PutBilling,'GrpName':GrpName,'KostakRetailCount':KostakRetailCount,'KostakRetailAlloted':KostakRetailAlloted,'KostakRetailBilling':KostakRetailBilling,'KostakSHNICount':KostakSHNICount,'KostakSHNIAlloted':KostakSHNIAlloted,'KostakSHNIBilling':KostakSHNIBilling,'KostakBHNICount':KostakBHNICount,'KostakBHNIAlloted':KostakBHNIAlloted,'KostakBHNIBilling':KostakBHNIBilling,'SubjectToRetailCount':SubjectToRetailCount,'SubjectToRetailAlloted':SubjectToRetailAlloted,
            'SubjectToRetailBilling':SubjectToRetailBilling,'SubjectToRetailBilling':SubjectToRetailBilling,'SubjectToSHNICount':SubjectToSHNICount,'SubjectToSHNIAlloted':SubjectToSHNIAlloted,'SubjectToSHNIBilling':SubjectToSHNIBilling,'SubjectToBHNICount':SubjectToBHNICount,'SubjectToBHNIAlloted':SubjectToBHNIAlloted,'SubjectToBHNIBilling':SubjectToBHNIBilling
            }
        
        all_groups_checked = all(status[0] for status in Group_telly_status.values()) if Group_telly_status else False
        df = pd.DataFrame.from_records(Data)
        
        html_table = "<table id=\"example\" class=\"table table-bordered table-hover table-striped\" style=\"max-width: 100vw;\" >\n"
        html_table += "<thead><tr >"
        # html_table += "<th rowspan='3' style='text-align: center;'>Tally</th>"
        html_table += f"<th rowspan='3' scope='col' class='tableline'><input type='checkbox' id='master-tally-checkbox' {'checked' if all_groups_checked else ''} onchange='updateAllTellyStatus(this)'> Tally &nbsp;</th>"
        html_table += "<th rowspan='3' style='text-align: center;'>Group Name</th>"
        html_table += "<td colspan='9'>Kostak &nbsp;</td>"
        html_table += "<td colspan='9'>Subject To &nbsp;</td>"
        html_table += "<td colspan='2' rowspan='2' ><b>Premium &nbsp;</b></td>"
        html_table += "<td colspan='2' rowspan='2' ><b>OPTIONS &nbsp;</b></td>"
        html_table += "<td colspan='2' rowspan='2' scope='col'  class='tableline'>Total</td>"
        html_table += "</tr>\n"
        
        html_table += "<tr>"
        html_table += '<td colspan="3"  data-sort-type="numeric" scope="col"><b>Retail</b></td>'
        html_table += '<td colspan="3"  data-sort-type="numeric" scope="col"><b>SHNI</b></td>'
        html_table += '<td colspan="3"  data-sort-type="numeric" scope="col"><b>BHNI</b></td>'
        html_table += '<td colspan="3"  data-sort-type="numeric" scope="col"><b>Retail</b></td>'
        html_table += '<td colspan="3"  data-sort-type="numeric" scope="col"><b>SHNI</b></td>'
        html_table += '<td colspan="3"  data-sort-type="numeric" scope="col"><b>BHNI</b></td>'
        # html_table += '<td colspan="2"  data-sort-type="numeric" scope="col"> </td>'
        # html_table += '<td colspan="2" scope="col"  class="tableline"><b>Total</b></td>'
        html_table += "</tr>\n"
        
        html_table += "<tr>"
        html_table += "<td>Count</td>"
        html_table += "<td>Alloted</td>"
        html_table += "<td>Billing</td>"
        html_table += "<td>Count</td>"
        html_table += "<td>Alloted</td>"
        html_table += "<td>Billing</td>"
        html_table += "<td>Count</td>"
        html_table += "<td>Alloted</td>"
        html_table += "<td>Billing</td>"
        html_table += "<td>Count</td>"
        html_table += "<td>Alloted</td>"
        html_table += "<td>Billing</td>"
        html_table += "<td>Count</td>"
        html_table += "<td>Alloted</td>"
        html_table += "<td>Billing</td>"
        html_table += "<td>Count</td>"
        html_table += "<td>Alloted</td>"
        html_table += "<td>Billing</td>"
        html_table += "<td>Shares</td>"
        html_table += "<td>Billing</td>"
        html_table += "<td>Call Amount</td>"
        html_table += "<td>Put Amount</td>"
        html_table += "<td>Shares</td>"
        html_table += "<td>Amount</td>"
        html_table += "</tr></thead>"
        
        float_format = "{:.0f}"
        html_table += "<tbody style='text-align: center;white-space: nowrap;'>"
        for i, row in df.iterrows():
            html_table += "<tr style='text-align: center;'>"
            is_tallied, tally_time = Group_telly_status.get(row.GrpName, (False, ''))
            checked_attr = 'checked' if is_tallied else ''
            content_html = ""
            if tally_time:
                date_part, time_part = tally_time.split(" ", 1)
                prefix = "" if is_tallied else "Last: "
                content_html = f"{prefix}{date_part}<br>{time_part}"
            time_html = f"<div class='tally-time-div' style='font-size: 10px; font-weight: bold; color: #555; margin-top: 4px; line-height: 1.2;'>{content_html}</div>"
            html_table += f"<th style='text-align: center; vertical-align: middle; min-width: 80px;'><div style='display: flex; flex-direction: column; align-items: center; justify-content: center;'><input type='checkbox' name='selectGroup' value='{row.GrpName}' class='group-checkbox' {checked_attr} onchange='updateTellyStatus(this)' >{time_html}</div></th>"
            html_table += f"<th><a href='/{IPOid}/Order/{row.GrpName}/All/All' style='color:blue; text-decoration: underline;'>{row.GrpName}</a></th>"
            html_table += f"<td>"
            if row.KostakRetailCount != 0:
                html_table += f"<a style='color:blue; text-decoration-line: underline;'   href=\"/{IPOid}/Order/{row.GrpName}/Kostak/RETAIL\" data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY:{float_format.format(row.KostakRetailCountBuy)}     SELL:{float_format.format(row.KostakRetailCountSell)}\">"
                html_table += f"{int(row.KostakRetailCount)}</a>" 
            else:
                html_table += f"{int(row.KostakRetailCount)}"
            html_table += "</td>"
            html_table += f"<td data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY-K: {float_format.format(row.KostakRetailAllotedBuy)}     SELL-K: {float_format.format(row.KostakRetailAllotedSell)}  &#013;&#010;BUY-Sh:{float_format.format(row.KostakRetailBuyShares)}    SELL-Sh:{float_format.format(row.KostakRetailSellShares)}\">{row.KostakRetailAlloted}</td>"
            html_table += f"<td data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY: {float_format.format(row.KostakRetailBillingBuy)}     SELL: {float_format.format(row.KostakRetailBillingSell)}\">{float_format.format(row.KostakRetailBilling)}</td>"
            
            html_table += f"<td>"
            if row.KostakSHNICount != 0:
                html_table += f"<a style=\"color:blue; text-decoration-line: underline;\"   href=\"/{IPOid}/Order/{row.GrpName}/Kostak/SHNI\" data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY:{float_format.format(row.KostakSHNICountBuy)}     SELL:{float_format.format(row.KostakSHNICountSell)}\">"
                html_table += f"{int(row.KostakSHNICount)}</a>"  
            else:
                html_table += f"{int(row.KostakSHNICount)}"
            html_table += "</td>"
            html_table += f"<td data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY-K: {float_format.format(row.KostakSHNIAllotedBuy)}     SELL-K: {float_format.format(row.KostakSHNIAllotedSell)}  &#013;&#010;BUY-Sh:{float_format.format(row.KostakSHNIBuyShares)}    SELL-Sh:{float_format.format(row.KostakSHNISellShares)}\">{row.KostakSHNIAlloted}</td>"
            html_table += f"<td data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY: {float_format.format(row.KostakSHNIBillingBuy)}     SELL: {float_format.format(row.KostakSHNIBillingSell)}\">{float_format.format(row.KostakSHNIBilling)}</td>"
            
            html_table += f"<td>"
            if row.KostakBHNICount != 0:
                html_table += f"<a style=\"color:blue; text-decoration-line: underline;\"   href=\"/{IPOid}/Order/{row.GrpName}/Kostak/BHNI\" data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY:{float_format.format(row.KostakBHNICountBuy)}     SELL:{float_format.format(row.KostakBHNICountSell)}\">"
                html_table += f"{int(row.KostakBHNICount)}</a>" 
            else:
                html_table += f"{int(row.KostakBHNICount)}"
            html_table += "</td>"
            html_table += f"<td data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY-K: {float_format.format(row.KostakBHNIAllotedBuy)}     SELL-K: {float_format.format(row.KostakBHNIAllotedSell)}  &#013;&#010;BUY-Sh:{float_format.format(row.KostakBHNIBuyShares)}    SELL-Sh:{float_format.format(row.KostakBHNISellShares)}\">{row.KostakBHNIAlloted}</td>"
            html_table += f"<td data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY: {float_format.format(row.KostakBHNIBillingBuy)}     SELL: {float_format.format(row.KostakBHNIBillingBuy)}\">{float_format.format(row.KostakBHNIBilling)}</td>"
            
            html_table += f"<td>"
            if row.SubjectToRetailCount != 0:
                html_table += f"<a style=\"color:blue; text-decoration-line: underline;\"   href=\"/{IPOid}/Order/{row.GrpName}/Subject To/RETAIL\" data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY:{float_format.format(row.SubjectToRetailCountBuy)}     SELL:{float_format.format(row.SubjectToRetailCountSell)}\">"
                html_table += f"{int(row.SubjectToRetailCount)}</a>"
            else:
                html_table += f"{int(row.SubjectToRetailCount)}"
            html_table += "</td>"
            html_table += f"<td data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY-S: {float_format.format(row.SubjectToRetailAllotedBuy)}     SELL-S: {float_format.format(row.SubjectToRetailAllotedSell)}  &#013;&#010;BUY-Sh:{float_format.format(row.SubjectToRetailBuyShares)}    SELL-Sh:{float_format.format(row.SubjectToRetailSellShares)}\">{row.SubjectToRetailAlloted}</td>"
            html_table += f"<td data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY: {float_format.format(row.SubjectToRetailBillingBuy)}     SELL: {float_format.format(row.SubjectToRetailBillingSell)}\">{float_format.format(row.SubjectToRetailBilling)}</td>"
            
            html_table += f"<td>"
            if row.SubjectToSHNICount != 0:
                html_table += f"<a style=\"color:blue; text-decoration-line: underline;\"   href=\"/{IPOid}/Order/{row.GrpName}/Subject To/SHNI\" data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY:{float_format.format(row.SubjectToSHNICountBuy)}     SELL:{float_format.format(row.SubjectToSHNICountSell)}\">"
                html_table += f"{int(row.SubjectToSHNICount)}</a>" 
            else:
                html_table += f"{int(row.SubjectToSHNICount)}"
            html_table += "</td>"
            html_table += f"<td data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY-S: {float_format.format(row.SubjectToSHNIAllotedBuy)}     SELL-S: {float_format.format(row.SubjectToSHNIAllotedSell)}  &#013;&#010;BUY-Sh:{float_format.format(row.SubjectToSHNIBuyShares)}    SELL-Sh:{float_format.format(row.SubjectToSHNISellShares)}\">{float_format.format(row.SubjectToSHNIAlloted)}</td>"
            html_table += f"<td data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY: {float_format.format(row.SubjectToSHNIBillingBuy)}     SELL: {float_format.format(row.SubjectToSHNIBillingSell)}\">{float_format.format(row.SubjectToSHNIBilling)}</td>"
           
            html_table += f"<td>"
            if row.SubjectToBHNICount != 0:
                html_table += f"<a style=\"color:blue; text-decoration-line: underline;\"   href=\"/{IPOid}/Order/{row.GrpName}/Subject To/BHNI\"0 data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY:{float_format.format(row.SubjectToBHNICountBuy)}     SELL:{float_format.format(row.SubjectToBHNICountSell)}\">"
                html_table += f"{int(row.SubjectToBHNICount)}</a>"
            else:
                html_table += f"{int(row.SubjectToBHNICount)}"
            html_table += "</td>"
            html_table += f"<td data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY-S: {float_format.format(row.SubjectToBHNIAllotedBuy)}     SELL-S: {float_format.format(row.SubjectToBHNIAllotedSell)}  &#013;&#010;BUY-Sh:{float_format.format(row.SubjectToBHNIBuyShares)}    SELL-Sh:{float_format.format(row.SubjectToBHNISellShares)}\">{row.SubjectToBHNIAlloted}</td>"
            html_table += f"<td data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY: {float_format.format(row.SubjectToBHNIBillingBuy)}     SELL: {float_format.format(row.SubjectToBHNIBillingSell)}\">{float_format.format(row.SubjectToBHNIBilling)}</td>"
           
            # html_table += f"<td data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY: {float_format.format(row.PremiumBuyShares)}     SELL: {float_format.format(row.PremiumSellShares)}\">{int(row.PremiumShares)}</td>"
            html_table += f"<td>"
            if row.PremiumShares != 0:
                html_table += f"<a style=\"color:blue; text-decoration-line: underline;\"   href=\"/{IPOid}/Order/{row.GrpName}/Premium/PREMIUM\" data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY: {float_format.format(row.PremiumBuyShares)}     SELL: {float_format.format(row.PremiumSellShares)}\">"
                html_table += f"{int(row.PremiumShares)}</a>"
            else:
                html_table += f"{int(row.PremiumShares)}"
            html_table += "</td>"
            
            html_table += f"<td data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY: {row.PremiumBuyBilling}     SELL: {float_format.format(row.PremiumSellBilling)}\">{float_format.format(row.PremiumBilling)}</td>"
            
            html_table += f"<td data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY: {float_format.format(row.CallBuyBilling)}     SELL: {float_format.format(row.CallSellBilling)}\">{float_format.format(row.CallBilling)}</td>"
            html_table += f"<td data-toggle=\"tooltip\" data-placement=\"auto\" title=\"BUY: {float_format.format(row.PutBuyBilling)}     SELL: {float_format.format(row.PutSellBilling)}\">{float_format.format(row.PutBilling)}</td>"
            
            html_table += f"<td data-toggle=\"tooltip\" data-placement=\"auto\" title=\"Kostak:{float_format.format(row.KostakShares)}     Subject To:{float_format.format(row.SubjectToShares)}     Premium:{float_format.format(row.PremiumShares)}\" >{float_format.format(row.Totalshares)}</td>"
            html_table += f"<td>{float_format.format(row.TotalAmount)}</td>"
            html_table += "</tr>\n"           
        html_table += "</tbody></table>"
        return render(request, 'Status.html', {'html_table':html_table,"IPOName": IPOName, "IPOid": IPOid,'page_obj': page_obj,'status_page_size':page_size})

#group wise dashboard payment fun
@allowed_users(allowed_roles=['Broker'])
def AddPayment(request):
    Group = GroupDetail.objects.filter(user=request.user)
    if request.method == "POST":
        GroupName = request.POST.get('Group', '')
        Amount = request.POST.get('Amount', '')

        group = Group.get(GroupName=GroupName, user=request.user)
        group.Collection = group.Collection + float(Amount)
        group.save()
    return redirect('/GroupWiseDashboard')

@allowed_users(allowed_roles=['Broker'])
def GroupWiseDashboard(request):
    Group = GroupDetail.objects.filter(user=request.user)
    IPO = CurrentIpoName.objects.filter(user=request.user)
    ipos = CurrentIpoName.objects.filter(user=request.user)
    groups = GroupDetail.objects.filter(user=request.user).order_by('GroupName')
    grpname = []
    Collectionlist = []
    IPOName = []
    IPOAmount = []
    nlist = []
    l = []
    Total = 0
    all_grpname = []
    JV_list = []
    
    # for Group_name in Group:
    #     all_grpname.append(Group_name)
    all_grpname = list(Group)

    page_obj = None
    try:
        page_size = request.POST.get('GWD_page_size')
        if page_size != '' and page_size != None:
            request.session['GWD_page_size'] = page_size
        else:
            page_size = request.session['GWD_page_size']
    except:
        page_size = request.session.get('GWD_page_size', 50)

    if page_size == 'All':
        all_rows = True
        paginator = Paginator(Group,len(Group))
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
    else:
        paginator = Paginator(Group, page_size)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
    
    jv_qs = (
        Accounting.objects.filter(
            user=request.user,
            group__in=page_obj,
            jv=True,
            is_deleted=False,
        )
        .values('group_id')
        .annotate(
            total=Coalesce(
                Sum(
                    Case(
                        When(amount_type='credit', then=F('amount')),
                        When(amount_type='debit', then=F('amount') * -1),
                        output_field=DecimalField()
                    ),
                    output_field=DecimalField()
                ),
                Decimal('0.0')
            )
        )
    )

    JV_lookup = {entry['group_id']: entry['total'] for entry in jv_qs}
    JV_list = [JV_lookup.get(group.id, 0) for group in page_obj]
    order_totals = (
        Order.objects.filter(user=request.user)
        .values("OrderIPOName")                # group by IPO id
        .annotate(total_amount=Sum("Amount"))  # sum Amount per IPO
    )
    Total = 0
    # 3. Convert into dict for O(1) lookup
    order_dict = {o["OrderIPOName"]: o["total_amount"] for o in order_totals}
        
    for ipo in ipos:
        total = order_dict.get(ipo.id, 0)  # if no orders → 0
        Total += total

        if ipo.IPOPrice != ipo.PreOpenPrice:
            IPOAmount.append(total)
        else:
            IPOAmount.append(0)

        IPOName.append(ipo)


    lenofipo = len(IPOName)
    for j in range(0, lenofipo):
        l.append(j)
    SumCollection = 0
    for GroupName, jv in zip(page_obj, JV_list):
        total_collection = GroupName.Collection    # Collection + JV
        SumCollection += total_collection
        Collectionlist.append(total_collection)        # use this for table
        grpname.append(GroupName)
    all_groups = GroupDetail.objects.filter(user=request.user)
    
    accounting_qs = (
        Accounting.objects.filter(
            user=request.user,
            group__in=all_groups,
            ipo__in=IPOName,
            is_deleted=False,
        )
        .values('group_id', 'ipo_id')
        .annotate(
            total=Sum(
                Case(
                    When(amount_type='credit', then=F('amount')),
                    When(amount_type='debit', then=-F('amount')),
                    output_field=DecimalField()
                )
            )
        )
    )
    
    accounting_lookup = {
        (row['group_id'], row['ipo_id']): float(row['total'] or 0)
        for row in accounting_qs
    }
    orders_qs = (
        Order.objects.filter(user=request.user, OrderGroup__in=page_obj, OrderIPOName__in=IPOName)
        .values('OrderGroup_id', 'OrderIPOName_id')
        .annotate(total=Sum('Amount'))
    )

    orders_lookup = {
        (row['OrderGroup_id'], row['OrderIPOName_id']): float(row['total'] or 0)
        for row in orders_qs
    }
    
    accountingTotal = {}
    # accounting_amount_dict = {}
    for GroupName in page_obj:
        IPOTotal = []
        # accountingTotal = []
        for IpoName in IPOName:
            if IpoName.IPOName in accountingTotal:
                total1 = accountingTotal[IpoName.IPOName]
            else:
                total1 = 0
                
            if IpoName.IPOPrice != IpoName.PreOpenPrice:

                key = (GroupName.id, IpoName.id)
                total = orders_lookup.get(key, 0)
                accounting_amount = accounting_lookup.get(key, 0.0)
                total1 = total1 + accounting_amount
            else:
                total = 0
                # accounting_amount_dict[(GroupName.id, IpoName.id)] = 0
            IPOTotal.append(total)
            # accountingTotal.append(total1)
            accountingTotal[IpoName.IPOName] = total1
        nlist.append(IPOTotal)

    # total_jv = sum(JV_list)
    accounting_dict = {}


    # qs = (
    #     Accounting.objects.filter(user=request.user, group__in=all_groups, ipo__in=IPOName)
    #     .values('group', 'ipo')
    #     .annotate(
    #         total=Sum(
    #             Case(
    #                 When(amount_type='credit', then=F('amount')),
    #                 When(amount_type='debit', then=-F('amount')),
    #                 output_field=DecimalField()
    #             )
    #         )
    #     )
    # )

    accounting_dict = {(entry['group_id'], entry['ipo_id']): entry['total'] or 0 for entry in accounting_qs}
    
    # Precompute due amounts for all group-IPO combinations
    due_dict = {}  # (group.id, ipo.id) -> due_amount

    order_totals = (
        Order.objects
        .filter(user=request.user)
        .values("OrderGroup_id", "OrderIPOName_id")
        .annotate(total=Sum("Amount"))
    )

    # Convert to dictionary for O(1) lookup
    order_totals_dict = {
        (row["OrderGroup_id"], row["OrderIPOName_id"]): row["total"] or 0
        for row in order_totals
    }

    # Now your loop uses pre-fetched data instead of hitting DB again
    for group in all_groups:
        for ipo in IPOName:
            if ipo.IPOPrice != ipo.PreOpenPrice:
                total_order_amount = order_totals_dict.get((group.id, ipo.id), 0)

                accounting_amount1 = accounting_dict.get((group.id, ipo.id), 0)
                due_amount = float(total_order_amount) - float(accounting_amount1)
                
                due_dict[(group.id, ipo.id)] = due_amount
            else:
                due_dict[(group.id, ipo.id)] = 0
    CollectionTotalPerGroup = []
    for group in page_obj:  # or all_groups if needed
        total_collection_for_group = 0
        for ipo in IPOName:
            if ipo.IPOPrice != ipo.PreOpenPrice:
                total_collection_for_group += accounting_lookup.get((group.id, ipo.id), 0)
        CollectionTotalPerGroup.append(total_collection_for_group)
    # for group in all_groups:
    #     for ipo, ipo_amount in zip(IPOName, IPOAmount):
    #         # Skip IPOs where IPOPrice == PreOpenPrice
    #         if ipo.IPOPrice != ipo.PreOpenPrice:
    #             total_order_amount = Order.objects.filter(
    #                 user=request.user,
    #                 OrderGroup=group,
    #                 OrderIPOName=ipo
    #             ).aggregate(total=Sum('Amount'))['total'] or 0

    #             accounting_amount1 = accounting_dict.get((group.id, ipo.id), 0)
    #             due_amount = float(total_order_amount) - float(accounting_amount1)
                
    #             due_dict[(group.id, ipo.id)] = due_amount
    #         else:
    #             due_dict[(group.id, ipo.id)] = 0
    # print(due_dict)

    dfi = pd.DataFrame({'IPOAmount':IPOAmount})
    df = pd.DataFrame(nlist, columns=IPOName, index=grpname)
    df['JV'] = JV_list    # <-- new JV column
    df['Total'] = df[IPOName].sum(axis=1)
    df['Collection'] = Collectionlist
    df['New Collection'] = CollectionTotalPerGroup
    df['Due Amount'] = df['Total'] - df['New Collection']
    DueAmountSum = Total - SumCollection
    
    html_table = "<table>\n"
    html_table = "<thead><tr style='text-align: center;'>"
    html_table += "<th class='sticky-col' >Group Name</th>"
    
    for i, ipo in enumerate(IPOName):
        
        # ipo_total = Decimal(dfi.loc[i, 'IPOAmount'])
        # ipo_total = Decimal(float(dfi.loc[i, 'IPOAmount']))
        ipo_total = Decimal(float(dfi.loc[i, 'IPOAmount'])).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
        acc_total = sum(accounting_dict.get((group.id, ipo.id), 0) for group in all_groups)
        acc_total = Decimal(acc_total).quantize(Decimal('0.1'),rounding=ROUND_HALF_UP)
        footer_due = float(ipo_total - acc_total)
        # all_due_zero = True
        # # for index, row in df.iterrows():
        # for group in all_groups:
           
        #     # accounting_amount1 = accounting_dict.get((group.id, ipo.id), 0)
        #     # due_amount = due_dict.get((group.id, ipo.id), 0)
        #     # if float(accounting_amount1) != 0 or float(due_amount) != 0:   
        #     #     all_due_zero = False
        #     #     break
        #     due_val = float(due_dict.get((group.id, ipo.id), 0))
        #     # if any due is not exactly zero, hide the delete button
        #     if round(due_val, 2) != 0.0:
        #         all_due_zero = False
        #         break
        #     print(due_val)
        html_table += "<th>"
        html_table += f"{ipo.IPOName} "

        # if all_due_zero:
        if round(footer_due, 2) == 0.0:
            html_table += f'''
                
                <button class="btn btn-sm delete-btn" title="Delete IPO"
                    data-toggle="modal" data-target="#deleteModal-{ipo.id}">
                    <i class="far fa-trash-alt icon-outline"></i>
                    <i class="fas fa-trash-alt icon-solid"></i>
                </button>
            '''
        
        html_table += "</th>"
        
    html_table += "<th>JV</th><th>Total</th><th title=\"This column will be removed soon\">Old Collection</th><th>Collection</th><th>Due Amount</th>"
    # for col in df.columns:
    #     html_table += f"<td style='background :rgb(182, 182, 158)'>{col}</td>"
    html_table += "</tr></thead>\n" 
    
    html_table += "<tbody style='text-align: center;white-space: nowrap;'>"
    float_format = "{:.0f}"
    for index, row in df.iterrows():
        html_table += "<tr style='text-align: center;'>"
        html_table += f"<th>{index}</th>"
        group_collection_sum = 0
        for ipo in IPOName:
            accounting_amount = accounting_dict.get((index.id, ipo.id), 0)
            group_collection_sum += float(accounting_amount)
        for col_name, cell in row.items():
            if col_name != 'JV' and col_name != 'Total' and col_name != 'Collection' and col_name != 'Due Amount' and col_name != 'New Collection':
                # For IPO amount cells, add data attributes
                ipo = IPOName[list(df.columns).index(col_name)]
                
                accounting_amount1 = accounting_dict.get((index.id, ipo.id), 0)
                due_amount = float(cell) - float(accounting_amount1)
                
                html_table += f'<td title= "Double Click To pay" class="amount-cell" data-ipo-id="{ipo.id}" data-ipo-name="{col_name}" data-group-id="{index.id}" data-group-name="{index}">Total: {float_format.format(cell)}<br>Collection: {float_format.format(accounting_amount1)} <br> Due: {float_format.format(due_amount)}</td>'
            elif col_name == 'Collection':
                html_table += f"<td title='This column will be removed soon'>{float_format.format(cell)}</td>"
            
            elif col_name == 'JV':
                jv_amount = JV_lookup.get(index.id, 0)
                flipped_jv = -jv_amount
                # Show + or - depending on sign
                if jv_amount >= 0:
                    html_table += f'<td title="Double Click to Pay" class="jv-cell" data-group-id="{index.id}" data-group-name="{index}" data-jv-amount="{flipped_jv}" > {float_format.format(flipped_jv)}</td>'
                else:
                    html_table += f'<td title="Double Click To Pay Jv Amount" class="jv-cell" data-group-id="{index.id}" data-group-name="{index}" data-jv-amount="{flipped_jv}">{float_format.format(flipped_jv)}</td>'
            
            elif col_name == 'New Collection':
                jv_amount = JV_lookup.get(index.id, 0)
                new_collection_total = float(group_collection_sum) + float(jv_amount)
                html_table += f"<td>{float_format.format(new_collection_total)}</td>"
            
            elif col_name == 'Due Amount':
                total_value = float(row['Total'])
                jv_amount = JV_lookup.get(index.id, 0)
                new_collection_total = float(group_collection_sum) + float(jv_amount)
                due_amount = total_value - new_collection_total
                # html_table += f"<td>{float_format.format(due_amount)}</td>"
                html_table += f'<td title="Double Click to Pay Due Amount" class="due-amount-cell" data-group-id="{index.id}" data-group-name="{index}" data-due-amount="{due_amount}">{float_format.format(due_amount)}</td>'
            else:
                html_table += f"<td>{float_format.format(cell)}</td>"
            
        html_table += "</tr>\n"
    html_table += "</tbody>"
    html_table += "<tfoot><tr>"
    html_table += "<th>Total</th>"
    # for i,row in dfi.iterrows():
    #     html_table += f"<td ondblclick=\"transaction_title()\">{float_format.format(row['IPOAmount'])}</td>"
    total_new_collection_footer = sum(Decimal(str(x)) for x in CollectionTotalPerGroup) + sum(JV_list)
    acc_grand_total, due_grand_total = Decimal('0.0'),Decimal('0.0')
    for ipo in IPOName:
        # ipo_total = Decimal(dfi.loc[IPOName.index(ipo), 'IPOAmount'])
        ipo_total = Decimal(float(dfi.loc[IPOName.index(ipo), 'IPOAmount']))
        acc_total = sum(accounting_dict.get((group.id, ipo.id),0) for group in all_groups)
        # due_total = sum(due_dict.get((group.id, ipo.id), 0) for group in all_groups)
        due_total = ipo_total - acc_total
        
        acc_grand_total += acc_total
        due_grand_total += due_total
        # html_table += f"<td>"
        # html_table += f"Total: {float_format.format(ipo_total)}<br>"
        # html_table += f"Collection: {float_format.format(acc_total)}<br>"
        # html_table += f"Due: {float_format.format(due_total)}"
        # html_table += "</td>"
        html_table += f"""
            <td>
                Total: {float_format.format(ipo_total)}<br>
                Collection: {float_format.format(acc_total)}<br>
                Due: {float_format.format(due_total)}
            </td>
        """
    html_table += f"<td>{float_format.format(sum(JV_list))}</td>" 
    html_table += f"<td>{float_format.format(Total)}</td>"
    html_table += f"<td>{float_format.format(SumCollection)}</td>"
    html_table += f"<td>{float_format.format(total_new_collection_footer)}</td>" 
    html_table += f"<td>{float_format.format(DueAmountSum)}</td>"
    html_table += "</tr></tfoot>"
    html_table += "</table>"
    
    entry_sorted = sorted(all_grpname,  key=lambda x: x.GroupName.lower())
    return render(request, 'GroupWiseDashboard.html', {'entry_sorted':entry_sorted,'entry': grpname, 'lenofipo': l,"ipos": ipos, "groups": groups, 'IPOName': IPOName, 'html_table': html_table,'IPOAmount':IPOAmount,'Total':Total,'SumCollection':SumCollection,'DueAmountSum':DueAmountSum,'page_obj': page_obj,'GWD_page_size':page_size})

def group_billing_details(request, group_id=None):
    if not request.user.is_authenticated:
        return redirect('login')
        
    groups = GroupDetail.objects.filter(user=request.user).order_by('GroupName')
    
    selected_group = None
    groups_to_process = []
    
    if group_id:
        selected_group = get_object_or_404(GroupDetail, id=group_id, user=request.user)
        groups_to_process = [selected_group]
    else:
        groups_to_process = list(groups)
        
    group_tables = []
    empty_groups = []
    
    ipos = CurrentIpoName.objects.filter(user=request.user).order_by('-id')
    
    for current_group in groups_to_process:
        sme_html_table = ""
        mainboard_html_table = ""
        
        # 1. Process SME IPOs
    
        # 1. Process SME IPOs
        sme_ipos = ipos.filter(IPOType="SME")
        sme_data = []
        for ipo in sme_ipos:
            orders = Order.objects.filter(user=request.user, OrderIPOName=ipo, OrderGroup=current_group)
            if not orders.exists():
                continue
            
            is_tally = all(str(o.Telly).lower() == 'true' or o.Telly == '1' or o.Telly == 1 for o in orders)
            
            ts_str = ""
            latest_tally_time = orders.aggregate(Max('tally_timestamp'))['tally_timestamp__max']
            if latest_tally_time:
                time_str = timezone.localtime(latest_tally_time).strftime('%d-%m-%Y<br>%H:%M:%S')
                if is_tally:
                    ts_str = time_str
                else:
                    ts_str = f"Last: {time_str}"

            orderdetails = OrderDetail.objects.filter(user=request.user, Order__OrderIPOName=ipo, Order__OrderGroup=current_group)
        
            # Kostak
            kostak_orders = orders.filter(OrderCategory="Kostak")
            kostak_buy_qty = kostak_orders.filter(OrderType="BUY").aggregate(Sum('Quantity'))['Quantity__sum'] or 0
            kostak_sell_qty = kostak_orders.filter(OrderType="SELL").aggregate(Sum('Quantity'))['Quantity__sum'] or 0
            kostak_count = kostak_buy_qty - kostak_sell_qty
        
            kostak_buy_alloted = orderdetails.filter(~Q(AllotedQty=None), ~Q(AllotedQty=0), Order__OrderCategory="Kostak", Order__OrderType="BUY").count()
            kostak_sell_alloted = orderdetails.filter(~Q(AllotedQty=None), ~Q(AllotedQty=0), Order__OrderCategory="Kostak", Order__OrderType="SELL").count()
            kostak_alloted = kostak_buy_alloted - kostak_sell_alloted
        
            kostak_buy_amt = kostak_orders.filter(OrderType="BUY").aggregate(Sum('Amount'))['Amount__sum'] or 0
            kostak_sell_amt = kostak_orders.filter(OrderType="SELL").aggregate(Sum('Amount'))['Amount__sum'] or 0
            kostak_billing = kostak_buy_amt + kostak_sell_amt
        
            # Subject To
            st_orders = orders.filter(OrderCategory="Subject To")
            st_buy_qty = st_orders.filter(OrderType="BUY").aggregate(Sum('Quantity'))['Quantity__sum'] or 0
            st_sell_qty = st_orders.filter(OrderType="SELL").aggregate(Sum('Quantity'))['Quantity__sum'] or 0
            st_count = st_buy_qty - st_sell_qty
        
            st_buy_alloted = orderdetails.filter(~Q(AllotedQty=None), ~Q(AllotedQty=0), Order__OrderCategory="Subject To", Order__OrderType="BUY").count()
            st_sell_alloted = orderdetails.filter(~Q(AllotedQty=None), ~Q(AllotedQty=0), Order__OrderCategory="Subject To", Order__OrderType="SELL").count()
            st_alloted = st_buy_alloted - st_sell_alloted
        
            st_buy_amt = st_orders.filter(OrderType="BUY").aggregate(Sum('Amount'))['Amount__sum'] or 0
            st_sell_amt = st_orders.filter(OrderType="SELL").aggregate(Sum('Amount'))['Amount__sum'] or 0
            st_billing = st_buy_amt + st_sell_amt
        
            # Premium
            premium_orders = orders.filter(OrderCategory="Premium")
            premium_buy_qty = premium_orders.filter(OrderType="BUY").aggregate(Sum('Quantity'))['Quantity__sum'] or 0
            premium_sell_qty = premium_orders.filter(OrderType="SELL").aggregate(Sum('Quantity'))['Quantity__sum'] or 0
            premium_count = premium_buy_qty - premium_sell_qty
        
            premium_buy_amt = premium_orders.filter(OrderType="BUY").aggregate(Sum('Amount'))['Amount__sum'] or 0
            premium_sell_amt = premium_orders.filter(OrderType="SELL").aggregate(Sum('Amount'))['Amount__sum'] or 0
            premium_billing = premium_buy_amt + premium_sell_amt
        
            # Totals
            kostak_buy_alloted_qty = orderdetails.filter(~Q(AllotedQty=None), ~Q(AllotedQty=0), Order__OrderCategory="Kostak", Order__OrderType="BUY").aggregate(Sum('AllotedQty'))['AllotedQty__sum'] or 0
            kostak_sell_alloted_qty = orderdetails.filter(~Q(AllotedQty=None), ~Q(AllotedQty=0), Order__OrderCategory="Kostak", Order__OrderType="SELL").aggregate(Sum('AllotedQty'))['AllotedQty__sum'] or 0
            total_kostak_alloted_shares = kostak_buy_alloted_qty - kostak_sell_alloted_qty
        
            st_buy_alloted_qty = orderdetails.filter(~Q(AllotedQty=None), ~Q(AllotedQty=0), Order__OrderCategory="Subject To", Order__OrderType="BUY").aggregate(Sum('AllotedQty'))['AllotedQty__sum'] or 0
            st_sell_alloted_qty = orderdetails.filter(~Q(AllotedQty=None), ~Q(AllotedQty=0), Order__OrderCategory="Subject To", Order__OrderType="SELL").aggregate(Sum('AllotedQty'))['AllotedQty__sum'] or 0
        #     total_share = premium_count + total_kostak_alloted_shares + total_st_alloted_shares
            total_amount = kostak_billing + st_billing + premium_billing
        
            sme_data.append({
                'ipo_name': ipo.IPOName,
                'ipo_id': ipo.id,
                'is_tally': is_tally,
                'ts_str': ts_str,
                'kostak_count': kostak_count,
                'kostak_alloted': kostak_alloted,
                'kostak_billing': kostak_billing,
                'st_count': st_count,
                'st_alloted': st_alloted,
                'st_billing': st_billing,
                'premium_count': premium_count,
                'premium_billing': premium_billing,
                'total_share': total_share,
                'total_amount': total_amount,
                'buy_kostak_qty': kostak_buy_qty,
                'sell_kostak_qty': kostak_sell_qty,
                'buy_kostak_alloted': kostak_buy_alloted,
                'sell_kostak_alloted': kostak_sell_alloted,
                'buy_kostak_alloted_qty': kostak_buy_alloted_qty,
                'sell_kostak_alloted_qty': kostak_sell_alloted_qty,
                'buy_kostak_amt': kostak_buy_amt,
                'sell_kostak_amt': kostak_sell_amt,
                'buy_st_qty': st_buy_qty,
                'sell_st_qty': st_sell_qty,
                'buy_st_alloted': st_buy_alloted,
                'sell_st_alloted': st_sell_alloted,
                'buy_st_alloted_qty': st_buy_alloted_qty,
                'sell_st_alloted_qty': st_sell_alloted_qty,
                'buy_st_amt': st_buy_amt,
                'sell_st_amt': st_sell_amt,
                'buy_premium_qty': premium_buy_qty,
                'sell_premium_qty': premium_sell_qty,
                'buy_premium_amt': premium_buy_amt,
                'sell_premium_amt': premium_sell_amt,
                'total_kostak_alloted_shares': total_kostak_alloted_shares,
                'total_st_alloted_shares': total_st_alloted_shares,
            })
        
        # Build SME HTML Table
        if sme_data:
            sme_html_table = "<table id='smeBillingTable_{}'".format(current_group.id) + " class='table table-bordered table-hover table-striped' style=\"max-width: 97vw;\">\n"
            sme_html_table += "<thead><tr >"
            sme_html_table += "<th rowspan='2' scope='col' class='tableline' style='text-align: center; vertical-align: middle;'>Tally &nbsp;</th>"
            sme_html_table += "<th rowspan='2' scope='col' class='tableline' style='text-align: center; vertical-align: middle;'>IPO Name &nbsp;</th>"
            sme_html_table += "<th colspan='3' style='text-align: center; background-color: #d1ecf1;'>Kostak &nbsp;</th>"
            sme_html_table += "<th colspan='3' style='text-align: center; background-color: #d4edda;'>Subject To &nbsp;</th>"
            sme_html_table += "<th colspan='2' style='text-align: center; background-color: #fff3cd;'>Premium &nbsp;</th>"
            sme_html_table += "<th rowspan='2' scope='col' class='tableline' style='text-align: center; vertical-align: middle; background-color: #e2e3e5;'>Total Share &nbsp;</th>"
            sme_html_table += "<th rowspan='2' scope='col' class='tableline' style='text-align: center; vertical-align: middle; background-color: #e2e3e5;'>Total Amount &nbsp;</th>"
            sme_html_table += "</tr>\n"
            sme_html_table += "<tr>"
            sme_html_table += "<th style='text-align: center; background-color: #e3f2fd;'>Count</th>"
            sme_html_table += "<th style='text-align: center; background-color: #e3f2fd;'>Alloted</th>"
            sme_html_table += "<th style='text-align: center; background-color: #e3f2fd;'>Billing</th>"
            sme_html_table += "<th style='text-align: center; background-color: #e8f5e9;'>Count</th>"
            sme_html_table += "<th style='text-align: center; background-color: #e8f5e9;'>Alloted</th>"
            sme_html_table += "<th style='text-align: center; background-color: #e8f5e9;'>Billing</th>"
            sme_html_table += "<th style='text-align: center; background-color: #fff8e1;'>Count</th>"
            sme_html_table += "<th style='text-align: center; background-color: #fff8e1;'>Billing</th>"
            sme_html_table += "</tr></thead>"
        
            float_format = "{:.0f}"
            sme_html_table += "<tbody style='text-align: center;white-space: nowrap;'>"
            for row in sme_data:
                tr_class = "archived-ipo" if row.get("is_tally") else ""
                checked = "checked" if row.get("is_tally") else ""
                sme_html_table += f"<tr class='{tr_class}' style='text-align: center;'>"
                ts_val = row.get('ts_str', '')
                ts_html = f"<br><span class='tally-ts-span' style='font-size: 0.65rem; font-weight: normal;'>{ts_val}</span>"
                sme_html_table += f"<th><input type='checkbox' class='ipo-archive-checkbox' style='cursor: pointer; margin:0; transform: scale(1.2);' data-id='{row['ipo_id']}' data-group='{current_group.GroupName}' {checked} title='Tally status'>{ts_html}</th>"
                sme_html_table += f"<th><a href='/{row['ipo_id']}/Status' style='color:blue; text-decoration: underline;'>{row['ipo_name']}</a></th>"
                sme_html_table += f"<td>"
                if row['kostak_count'] != 0:
                    sme_html_table += f"<a style='color:blue; text-decoration-line: underline;' href='/{row['ipo_id']}/Order/{current_group.GroupName}/Kostak/All' data-toggle='tooltip' data-placement='auto' title='BUY:{int(row['buy_kostak_qty'])}     SELL:{int(row['sell_kostak_qty'])}'>{int(row['kostak_count'])}</a>"
                else:
                    sme_html_table += f"{int(row['kostak_count'])}"
                sme_html_table += "</td>"
                sme_html_table += f"<td data-toggle='tooltip' data-placement='auto' title='BUY:{row['buy_kostak_alloted']}     SELL:{row['sell_kostak_alloted']} &#013;&#010;BUY:{row['buy_kostak_alloted_qty']}     SELL:{row['sell_kostak_alloted_qty']}'>{int(row['kostak_alloted'])}</td>"
                sme_html_table += f"<td data-toggle='tooltip' data-placement='auto' title='BUY:{row['buy_kostak_amt']:.1f}     SELL:{row['sell_kostak_amt']:.1f}'>{row['kostak_billing']:.1f}</td>"
            
                sme_html_table += f"<td>"
                if row['st_count'] != 0:
                    sme_html_table += f"<a style='color:blue; text-decoration-line: underline;' href='/{row['ipo_id']}/Order/{current_group.GroupName}/Subject To/All' data-toggle='tooltip' data-placement='auto' title='BUY:{int(row['buy_st_qty'])}     SELL:{int(row['sell_st_qty'])}'>{int(row['st_count'])}</a>"
                else:
                    sme_html_table += f"{int(row['st_count'])}"
                sme_html_table += "</td>"
                sme_html_table += f"<td data-toggle='tooltip' data-placement='auto' title='BUY:{row['buy_st_alloted']}     SELL:{row['sell_st_alloted']} &#013;&#010;BUY:{row['buy_st_alloted_qty']}     SELL:{row['sell_st_alloted_qty']}'>{int(row['st_alloted'])}</td>"
                sme_html_table += f"<td data-toggle='tooltip' data-placement='auto' title='BUY:{row['buy_st_amt']:.1f}     SELL:{row['sell_st_amt']:.1f}'>{row['st_billing']:.1f}</td>"
            
                sme_html_table += f"<td>"
                if row['premium_count'] != 0:
                    sme_html_table += f"<a style='color:blue; text-decoration-line: underline;' href='/{row['ipo_id']}/Order/{current_group.GroupName}/Premium/All' data-toggle='tooltip' data-placement='auto' title='BUY:{int(row['buy_premium_qty'])}     SELL:{int(row['sell_premium_qty'])}'>{int(row['premium_count'])}</a>"
                else:
                    sme_html_table += f"{int(row['premium_count'])}"
                sme_html_table += "</td>"
                sme_html_table += f"<td data-toggle='tooltip' data-placement='auto' title='BUY:{row['buy_premium_amt']:.1f}     SELL:{row['sell_premium_amt']:.1f}'>{row['premium_billing']:.1f}</td>"
            
                sme_html_table += f"<td data-toggle='tooltip' data-placement='auto' title='Kostak:{row['total_kostak_alloted_shares']}     Subject To:{row['total_st_alloted_shares']}     Premium:{row['premium_count']}'>{int(row['total_share'])}</td>"
                sme_html_table += f"<td data-toggle='tooltip' data-placement='auto'>{row['total_amount']:.0f}</td>"
            
                sme_html_table += "</tr>\n"
            sme_html_table += "</tbody></table>"

        # 2. Process Mainboard IPOs
        mainboard_ipos = ipos.filter(IPOType="MAINBOARD")
        mainboard_data = []
        for ipo in mainboard_ipos:
            orders = Order.objects.filter(user=request.user, OrderIPOName=ipo, OrderGroup=current_group)
            if not orders.exists():
                continue
            
            is_tally = all(str(o.Telly).lower() == 'true' or o.Telly == '1' or o.Telly == 1 for o in orders)
            
            ts_str = ""
            latest_tally_time = orders.aggregate(Max('tally_timestamp'))['tally_timestamp__max']
            if latest_tally_time:
                time_str = timezone.localtime(latest_tally_time).strftime('%d-%m-%Y<br>%H:%M:%S')
                if is_tally:
                    ts_str = time_str
                else:
                    ts_str = f"Last: {time_str}"

            orderdetails = OrderDetail.objects.filter(user=request.user, Order__OrderIPOName=ipo, Order__OrderGroup=current_group)
        
            def get_cat_stats(category, inv_type):
                cat_orders = orders.filter(OrderCategory=category, InvestorType=inv_type)
                buy_qty = cat_orders.filter(OrderType="BUY").aggregate(Sum('Quantity'))['Quantity__sum'] or 0
                sell_qty = cat_orders.filter(OrderType="SELL").aggregate(Sum('Quantity'))['Quantity__sum'] or 0
                count = buy_qty - sell_qty
            
                buy_alloted = orderdetails.filter(~Q(AllotedQty=None), ~Q(AllotedQty=0), Order__OrderCategory=category, Order__OrderType="BUY", Order__InvestorType=inv_type).count()
                sell_alloted = orderdetails.filter(~Q(AllotedQty=None), ~Q(AllotedQty=0), Order__OrderCategory=category, Order__OrderType="SELL", Order__InvestorType=inv_type).count()
                alloted = buy_alloted - sell_alloted
            
                buy_alloted_qty = orderdetails.filter(~Q(AllotedQty=None), ~Q(AllotedQty=0), Order__OrderCategory=category, Order__OrderType="BUY", Order__InvestorType=inv_type).aggregate(Sum('AllotedQty'))['AllotedQty__sum'] or 0
                sell_alloted_qty = orderdetails.filter(~Q(AllotedQty=None), ~Q(AllotedQty=0), Order__OrderCategory=category, Order__OrderType="SELL", Order__InvestorType=inv_type).aggregate(Sum('AllotedQty'))['AllotedQty__sum'] or 0
            
                buy_amt = cat_orders.filter(OrderType="BUY").aggregate(Sum('Amount'))['Amount__sum'] or 0
                sell_amt = cat_orders.filter(OrderType="SELL").aggregate(Sum('Amount'))['Amount__sum'] or 0
                billing = buy_amt + sell_amt
            
                return {
                    'count': count, 'alloted': alloted, 'billing': billing,
                    'buy_qty': buy_qty, 'sell_qty': sell_qty,
                    'buy_alloted': buy_alloted, 'sell_alloted': sell_alloted,
                    'buy_alloted_qty': buy_alloted_qty, 'sell_alloted_qty': sell_alloted_qty,
                    'buy_amt': buy_amt, 'sell_amt': sell_amt
                }

            k_retail = get_cat_stats("Kostak", "RETAIL")
            k_shni = get_cat_stats("Kostak", "SHNI")
            k_bhni = get_cat_stats("Kostak", "BHNI")
        
            st_retail = get_cat_stats("Subject To", "RETAIL")
            st_shni = get_cat_stats("Subject To", "SHNI")
            st_bhni = get_cat_stats("Subject To", "BHNI")
        
            p_orders = orders.filter(OrderCategory="Premium")
            p_buy_qty = p_orders.filter(OrderType="BUY").aggregate(Sum('Quantity'))['Quantity__sum'] or 0
            p_sell_qty = p_orders.filter(OrderType="SELL").aggregate(Sum('Quantity'))['Quantity__sum'] or 0
            p_shares = p_buy_qty - p_sell_qty
        
            p_buy_amt = p_orders.filter(OrderType="BUY").aggregate(Sum('Amount'))['Amount__sum'] or 0
            p_sell_amt = p_orders.filter(OrderType="SELL").aggregate(Sum('Amount'))['Amount__sum'] or 0
            p_billing = p_buy_amt + p_sell_amt
        
            c_orders = orders.filter(OrderCategory="CALL")
            c_buy_amt = c_orders.filter(OrderType="BUY").aggregate(Sum('Amount'))['Amount__sum'] or 0
            c_sell_amt = c_orders.filter(OrderType="SELL").aggregate(Sum('Amount'))['Amount__sum'] or 0
            call_billing = c_buy_amt + c_sell_amt
        
            put_orders = orders.filter(OrderCategory="PUT")
            put_buy_amt = put_orders.filter(OrderType="BUY").aggregate(Sum('Amount'))['Amount__sum'] or 0
            put_sell_amt = put_orders.filter(OrderType="SELL").aggregate(Sum('Amount'))['Amount__sum'] or 0
            put_billing = put_buy_amt + put_sell_amt
        
            total_kostak_shares = (k_retail['buy_alloted_qty'] + k_shni['buy_alloted_qty'] + k_bhni['buy_alloted_qty']) - (k_retail['sell_alloted_qty'] + k_shni['sell_alloted_qty'] + k_bhni['sell_alloted_qty'])
            total_st_shares = (st_retail['buy_alloted_qty'] + st_shni['buy_alloted_qty'] + st_bhni['buy_alloted_qty']) - (st_retail['sell_alloted_qty'] + st_shni['sell_alloted_qty'] + st_bhni['sell_alloted_qty'])
            total_shares = total_kostak_shares + total_st_shares + p_shares
        
            total_amount = p_billing + k_retail['billing'] + k_shni['billing'] + k_bhni['billing'] + st_retail['billing'] + st_shni['billing'] + st_bhni['billing'] + call_billing + put_billing
        
            mainboard_data.append({
                'ipo_name': ipo.IPOName,
                'ipo_id': ipo.id,
                'is_tally': is_tally,
                'ts_str': ts_str,
                'k_retail': k_retail,
                'k_shni': k_shni,
                'k_bhni': k_bhni,
                'st_retail': st_retail,
                'st_shni': st_shni,
                'st_bhni': st_bhni,
                'p_shares': p_shares,
                'p_billing': p_billing,
                'call_billing': call_billing,
                'put_billing': put_billing,
                'total_shares': total_shares,
                'total_amount': total_amount,
                'p_buy_qty': p_buy_qty,
                'p_sell_qty': p_sell_qty,
                'p_buy_amt': p_buy_amt,
                'p_sell_amt': p_sell_amt,
                'c_buy_amt': c_buy_amt,
                'c_sell_amt': c_sell_amt,
                'put_buy_amt': put_buy_amt,
                'put_sell_amt': put_sell_amt,
                'total_kostak_shares': total_kostak_shares,
                'total_st_shares': total_st_shares,
            })
        
        # Build Mainboard HTML Table
        if mainboard_data:
            mainboard_html_table = "<table id=\"mainboardBillingTable_{}\"".format(current_group.id) + " class=\"table table-bordered table-hover table-striped\" style=\"max-width: 100vw; border-collapse: collapse; border-top: 1px solid #555; border-bottom: 1px solid #555; border-left: 1px solid #555;\" >\n"
            mainboard_html_table += "<thead><tr >"
            mainboard_html_table += "<th rowspan='3' scope='col' class='tableline' style='text-align: center; vertical-align: middle; border-left: 1px solid #555; border-right: 1px solid #555; border-bottom: 2px solid #555;'>Tally &nbsp;</th>"
            mainboard_html_table += "<th rowspan='3' style='text-align: center; vertical-align: middle; border-left: 1px solid #555; border-right: 1px solid #555; border-bottom: 2px solid #555;'>IPO Name</th>"
            mainboard_html_table += "<th colspan='9' style='text-align: center; background-color: #d1ecf1; border-left: 1px solid #555; border-right: 1px solid #555; border-bottom: 1px solid #555;'>Kostak &nbsp;</th>"
            mainboard_html_table += "<th colspan='9' style='text-align: center; background-color: #d4edda; border-left: 1px solid #555; border-right: 1px solid #555; border-bottom: 1px solid #555;'>Subject To &nbsp;</th>"
            mainboard_html_table += "<th colspan='2' rowspan='2' style='text-align: center; vertical-align: middle; background-color: #fff3cd; border-left: 1px solid #555; border-right: 1px solid #555; border-bottom: 1px solid #555;'>Premium &nbsp;</th>"
            mainboard_html_table += "<th colspan='2' rowspan='2' style='text-align: center; vertical-align: middle; background-color: #f8d7da; border-left: 1px solid #555; border-right: 1px solid #555; border-bottom: 1px solid #555;'>OPTIONS &nbsp;</th>"
            mainboard_html_table += "<th colspan='2' rowspan='2' scope='col' class='tableline' style='text-align: center; vertical-align: middle; background-color: #e2e3e5; border-left: 1px solid #555; border-right: 1px solid #555; border-bottom: 1px solid #555;'>Total</th>"
            mainboard_html_table += "</tr>\n"
        
            mainboard_html_table += "<tr>"
            mainboard_html_table += '<th colspan="3" data-sort-type="numeric" scope="col" style="text-align: center; background-color: #e3f2fd; border-left: 1px solid #555; border-right: 1px solid #555; border-bottom: 1px solid #555;">Retail</th>'
            mainboard_html_table += '<th colspan="3" data-sort-type="numeric" scope="col" style="text-align: center; background-color: #e3f2fd; border-right: 1px solid #555; border-bottom: 1px solid #555;">SHNI</th>'
            mainboard_html_table += '<th colspan="3" data-sort-type="numeric" scope="col" style="text-align: center; background-color: #e3f2fd; border-right: 1px solid #555; border-bottom: 1px solid #555;">BHNI</th>'
            mainboard_html_table += '<th colspan="3" data-sort-type="numeric" scope="col" style="text-align: center; background-color: #e8f5e9; border-left: 1px solid #555; border-right: 1px solid #555; border-bottom: 1px solid #555;">Retail</th>'
            mainboard_html_table += '<th colspan="3" data-sort-type="numeric" scope="col" style="text-align: center; background-color: #e8f5e9; border-right: 1px solid #555; border-bottom: 1px solid #555;">SHNI</th>'
            mainboard_html_table += '<th colspan="3" data-sort-type="numeric" scope="col" style="text-align: center; background-color: #e8f5e9; border-right: 1px solid #555; border-bottom: 1px solid #555;">BHNI</th>'
            mainboard_html_table += "</tr>\n"
        
            mainboard_html_table += "<tr>"
            k_sub = "<th style='text-align: center; background-color: #e3f2fd; border-left: 1px solid #555; border-bottom: 2px solid #555;'>Count</th><th style='text-align: center; background-color: #e3f2fd; border-bottom: 2px solid #555;'>Alloted</th><th style='text-align: center; background-color: #e3f2fd; border-right: 1px solid #555; border-bottom: 2px solid #555;'>Billing</th>"
            st_sub = "<th style='text-align: center; background-color: #e8f5e9; border-left: 1px solid #555; border-bottom: 2px solid #555;'>Count</th><th style='text-align: center; background-color: #e8f5e9; border-bottom: 2px solid #555;'>Alloted</th><th style='text-align: center; background-color: #e8f5e9; border-right: 1px solid #555; border-bottom: 2px solid #555;'>Billing</th>"
            mainboard_html_table += k_sub * 3
            mainboard_html_table += st_sub * 3
            mainboard_html_table += "<th style='text-align: center; background-color: #fff8e1; border-left: 1px solid #555; border-bottom: 2px solid #555;'>Shares</th><th style='text-align: center; background-color: #fff8e1; border-right: 1px solid #555; border-bottom: 2px solid #555;'>Billing</th>"
            mainboard_html_table += "<th style='text-align: center; background-color: #ffebee; border-left: 1px solid #555; border-bottom: 2px solid #555;'>Call Amount</th><th style='text-align: center; background-color: #ffebee; border-right: 1px solid #555; border-bottom: 2px solid #555;'>Put Amount</th>"
            mainboard_html_table += "<th style='text-align: center; background-color: #f5f5f5; border-left: 1px solid #555; border-bottom: 2px solid #555;'>Shares</th><th style='text-align: center; background-color: #f5f5f5; border-right: 1px solid #555; border-bottom: 2px solid #555;'>Amount</th>"
            mainboard_html_table += "</tr></thead>"
        
            float_format = "{:.0f}"
            mainboard_html_table += "<tbody style='text-align: center;white-space: nowrap;'>"
            for row in mainboard_data:
                tr_class = "archived-ipo" if row.get("is_tally") else ""
                checked = "checked" if row.get("is_tally") else ""
                mainboard_html_table += f"<tr class='{tr_class}' style='text-align: center;'>"
                ts_val = row.get('ts_str', '')
                ts_html = f"<br><span class='tally-ts-span' style='font-size: 0.65rem; font-weight: normal;'>{ts_val}</span>"
                mainboard_html_table += f"<th style='border-left: 1px solid #555; border-right: 1px solid #555;'><input type='checkbox' class='ipo-archive-checkbox' style='cursor: pointer; margin:0; transform: scale(1.2);' data-id='{row['ipo_id']}' data-group='{current_group.GroupName}' {checked} title='Tally status'>{ts_html}</th>"
                mainboard_html_table += f"<th style='border-left: 1px solid #555; border-right: 1px solid #555;'><a href='/{row['ipo_id']}/Status' style='color:blue; text-decoration: underline;'>{row['ipo_name']}</a></th>"
            
                for k_type in ['k_retail', 'k_shni', 'k_bhni']:
                    k = row[k_type]
                    inv = k_type.split('_')[1].upper()
                    k_left_border = " border-left: 1px solid #555;" if k_type == 'k_retail' else ""
                    mainboard_html_table += f"<td style='{k_left_border}'>"
                    if k['count'] != 0:
                        mainboard_html_table += f"<a style='color:blue; text-decoration-line: underline;' href='/{row['ipo_id']}/Order/{current_group.GroupName}/Kostak/{inv}' data-toggle='tooltip' data-placement='auto' title='BUY:{float_format.format(k['buy_qty'])}     SELL:{float_format.format(k['sell_qty'])}'>{int(k['count'])}</a>"
                    else:
                        mainboard_html_table += f"{int(k['count'])}"
                    mainboard_html_table += "</td>"
                
                    mainboard_html_table += f"<td data-toggle='tooltip' data-placement='auto' title='BUY-K: {k['buy_alloted']}     SELL-K: {k['sell_alloted']}  &#013;&#010;BUY-Sh:{float_format.format(k['buy_alloted_qty'])}    SELL-Sh:{float_format.format(k['sell_alloted_qty'])}'>{int(k['alloted'])}</td>"
                
                    k_right_border = " border-right: 1px solid #555;"
                    mainboard_html_table += f"<td style='{k_right_border}' data-toggle='tooltip' data-placement='auto' title='BUY: {float_format.format(k['buy_amt'])}     SELL: {float_format.format(k['sell_amt'])}'>{k['billing']:.1f}</td>"

                for st_type in ['st_retail', 'st_shni', 'st_bhni']:
                    st = row[st_type]
                    inv = st_type.split('_')[1].upper()
                    st_left_border = " border-left: 1px solid #555;" if st_type == 'st_retail' else ""
                    mainboard_html_table += f"<td style='{st_left_border}'>"
                    if st['count'] != 0:
                        mainboard_html_table += f"<a style='color:blue; text-decoration-line: underline;' href='/{row['ipo_id']}/Order/{current_group.GroupName}/Subject To/{inv}' data-toggle='tooltip' data-placement='auto' title='BUY:{float_format.format(st['buy_qty'])}     SELL:{float_format.format(st['sell_qty'])}'>{int(st['count'])}</a>"
                    else:
                        mainboard_html_table += f"{int(st['count'])}"
                    mainboard_html_table += "</td>"
                
                    mainboard_html_table += f"<td data-toggle='tooltip' data-placement='auto' title='BUY-S: {st['buy_alloted']}     SELL-S: {st['sell_alloted']}  &#013;&#010;BUY-Sh:{float_format.format(st['buy_alloted_qty'])}    SELL-Sh:{float_format.format(st['sell_alloted_qty'])}'>{int(st['alloted'])}</td>"
                
                    st_right_border = " border-right: 1px solid #555;"
                    mainboard_html_table += f"<td style='{st_right_border}' data-toggle='tooltip' data-placement='auto' title='BUY: {float_format.format(st['buy_amt'])}     SELL: {float_format.format(st['sell_amt'])}'>{st['billing']:.1f}</td>"

                mainboard_html_table += f"<td style='border-left: 1px solid #555;'>"
                if row['p_shares'] != 0:
                    mainboard_html_table += f"<a style='color:blue; text-decoration-line: underline;' href='/{row['ipo_id']}/Order/{current_group.GroupName}/Premium/All' data-toggle='tooltip' data-placement='auto' title='BUY:{float_format.format(row['p_buy_qty'])}     SELL:{float_format.format(row['p_sell_qty'])}'>{int(row['p_shares'])}</a>"
                else:
                    mainboard_html_table += f"{int(row['p_shares'])}"
                mainboard_html_table += "</td>"
            
                mainboard_html_table += f"<td style='border-right: 1px solid #555;' data-toggle='tooltip' data-placement='auto' title='BUY: {float_format.format(row['p_buy_amt'])}     SELL: {float_format.format(row['p_sell_amt'])}'>{row['p_billing']:.1f}</td>"
            
                mainboard_html_table += f"<td style='border-left: 1px solid #555;' data-toggle='tooltip' data-placement='auto' title='BUY: {float_format.format(row['c_buy_amt'])}     SELL: {float_format.format(row['c_sell_amt'])}'>{row['call_billing']:.1f}</td>"
                mainboard_html_table += f"<td style='border-right: 1px solid #555;' data-toggle='tooltip' data-placement='auto' title='BUY: {float_format.format(row['put_buy_amt'])}     SELL: {float_format.format(row['put_sell_amt'])}'>{row['put_billing']:.1f}</td>"
            
                mainboard_html_table += f"<td style='border-left: 1px solid #555;' data-toggle='tooltip' data-placement='auto' title='Kostak:{float_format.format(row['total_kostak_shares'])}     Subject To:{float_format.format(row['total_st_shares'])}     Premium:{float_format.format(row['p_shares'])}'>{int(row['total_shares'])}</td>"
                mainboard_html_table += f"<td style='border-right: 1px solid #555;'>{row['total_amount']:.0f}</td>"
                mainboard_html_table += "</tr>\n"
            mainboard_html_table += "</tbody></table>"

        if sme_html_table or mainboard_html_table:
            group_tables.append({
                'group': current_group,
                'sme_html_table': sme_html_table,
                'mainboard_html_table': mainboard_html_table
            })
        else:
            empty_groups.append(current_group.GroupName)

    return render(request, 'group_billing_details.html', {
        'groups': groups,
        'selected_group': selected_group,
        'group_tables': group_tables,
        'empty_groups': empty_groups,
    })

def BackUp(request):
    user = request.user
    entry = CurrentIpoName.objects.filter(user=request.user)

    entry = entry.order_by('-id') 

    page_obj = None
    try:
        page_size = request.POST.get('Backup_page_size')
        if page_size != '' and page_size != None:
            request.session['Backup_page_size'] = page_size
        else:
            page_size = request.session['Backup_page_size']
    except:
        page_size = request.session.get('Backup_page_size', 50)
   
    Data=[]
    if entry is not None and entry.exists():
    
        if page_size == 'All':
            all_rows = True
            paginator = Paginator(entry,len(entry))
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
        else:
            paginator = Paginator(entry, page_size)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
        
        start_index = (page_obj.number - 1) * page_obj.paginator.per_page
        for i,order_detail in enumerate(page_obj):
            entry_data = {
                'id':order_detail.id,
                'IPOName': order_detail.IPOName,
                'sr_no': start_index + i + 1
            }
            Data.append(entry_data)
    df = pd.DataFrame.from_records(Data)
    html_table = "<table >"
    html_table = "<thead class=\"table-sortable\"><tr style='text-align: center;white-space: nowrap;'>"
    html_table += "<th scope='col' style='width:10%;'>Sr No. &nbsp;</th>"
    html_table += "<th scope='col' style=\"width:75%;\">IPO Name &nbsp;</th>"
    html_table += "<th scope='col' style=\"width:15%;\">Action&nbsp;</th>"
    html_table += "</tr></thead>"
    html_table += "<tbody>"

    for i, row in df.iterrows():
        html_table += "<tr >"
        html_table += f"<th>{row.sr_no}</th>"
        html_table += f"<th>{row.IPOName}</th>"
        html_table += f"<td style='white-space: nowrap;'><button onclick=\"window.location.href='/{ row.id }/Backup/';\"\
                    class='btn btn-outline-primary' style='width: 72px;'>Backup</button></td> "
    
        html_table += "</tr>"
    html_table += "</tbody></table>"
    
    return render(request, 'Backup.html',{'html_table': html_table, 'user': user,'page_obj': page_obj,'Backup_page_size':page_size})

@allowed_users(allowed_roles=['Broker'])
def panalloted(request):
    Client = ClientDetail.objects.filter(user=request.user)
    IPO = CurrentIpoName.objects.filter(user=request.user)
    grpname = []
    IPOName = []
    nlist = []
    l = []
    for IpoName in IPO:
        IPOName.append(IpoName)
    lenofipo = len(IPOName)
    for j in range(0, lenofipo):
        l.append(j)
    for GroupName in Client:
        grpname.append(GroupName.PANNo)
    lenofgroup = len(grpname)

    for ClientPan in Client:
        IPOTotal = []
        for IpoName in IPO:
            try:
                entry = OrderDetail.objects.get(
                    user=request.user, OrderDetailPANNo=ClientPan, Order__OrderIPOName=IpoName)
                a = entry.AllotedQty
            except:
                a = None
            IPOTotal.append(a)
        nlist.append(IPOTotal)

    df = pd.DataFrame(nlist, columns=IPOName, index=grpname)
    return render(request, 'panalloted.html', {'entry': grpname, 'lenofipo': l, 'IPOTotal': IPOTotal, 'IPOName': IPOName, 'df': df})

@allowed_users(allowed_roles=['Broker'])
def autocomplete(request):
    if 'term' in request.GET:
        qs = ClientDetail.objects.filter(
            user=request.user, PANNo__istartswith=request.GET.get('term'))
        titles = list()
        for product in qs:
            titles.append(f"{product.PANNo}-{product.Name}")

        return JsonResponse(titles, safe=False)

@allowed_users(allowed_roles=['Broker'])
def autocomplete1(request):
    PAN = request.POST.get('PAN', '')
    q = ClientDetail.objects.filter(PANNo=PAN, user=request.user)
    Clients = list()
    for product in q:
        Clients.append(product.Name)
    return JsonResponse(Clients, safe=False)

def update_client_sync(c, name, group):
    # This runs in a synchronous thread where DB access is allowed
    if c.Name != name or c.Group != group:
        c.Name = name
        c.Group = group
        c.save()
        return True
    return False

async def handle_single_row(userid, PAN, clientname, allotedqty, DematNo, Application, rate, request, row_id, IPOid, OrderType, Groupfilter, IPOTypefilter, InvestorTypefilter, page_number, Order_idlist, clients_cache=None, assigned_pans_cache=None, update_alloted_only=False):
    try:
        employee = await sync_to_async(OrderDetail.objects.select_related('Order__OrderGroup', 'OrderDetailPANNo').get)(user_id=userid, id=row_id)
        order_group = employee.Order.OrderGroup

        if PAN:
            # Clean PAN
            cleaned_pan = re.sub(r'[^A-Za-z0-9]', '', str(PAN)).upper()
        
            # Use Cache if provided
            client = None
            if clients_cache is not None:
                client = clients_cache.get(cleaned_pan)
        
            if not client:
                # Fallback to DB if not in cache (though expected to be preloaded)
                client, created = await sync_to_async(ClientDetail.objects.update_or_create)(
                    user_id=userid,
                    PANNo=cleaned_pan,
                    defaults={'Name': clientname, 'Group': order_group}
                )
                if clients_cache is not None:
                    clients_cache[cleaned_pan] = client
            else:
                # Update existing client if name or group differs
                # if client.Name != clientname or client.Group != order_group:
                #     client.Name = clientname
                #     client.Group = order_group
                #     await sync_to_async(client.save)()
                await sync_to_async(update_client_sync)(client, clientname, order_group)

            # Check for duplicates using Cache
            exists_in_ipo = False
            if assigned_pans_cache is not None:
                # If PAN exists in cache and it's NOT our current row_id, it's a conflict
                if cleaned_pan in assigned_pans_cache and assigned_pans_cache[cleaned_pan] != int(row_id):
                    exists_in_ipo = True
            else:
                exists_in_ipo = await sync_to_async(
                    OrderDetail.objects.filter(
                        user_id=userid, 
                        Order__OrderIPOName_id=IPOid, 
                        Order__OrderType=OrderType, 
                        OrderDetailPANNo=client
                    ).exclude(id=row_id).exists
                )()

            if exists_in_ipo:
                # Allow quantity updates if the same PAN is kept
                current_pan_of_row = employee.OrderDetailPANNo.PANNo.upper().strip() if employee.OrderDetailPANNo else None
                if cleaned_pan != current_pan_of_row:
                    return

            employee.OrderDetailPANNo = client
            employee.DematNumber = DematNo
            employee.ApplicationNumber = Application
        
            # Update cache to reflect that this row now has this PAN
            if assigned_pans_cache is not None:
                assigned_pans_cache[cleaned_pan] = int(row_id)
        else:
            # Clear case (PAN is empty)
            employee.OrderDetailPANNo = None
            employee.DematNumber = ''
            employee.ApplicationNumber = ''

        # Commmon fields and Save
        if request.user.is_authenticated:
            employee.AllotedQty = None if allotedqty == '' else allotedqty
        
        await sync_to_async(employee.save)()

        if employee.Order_id not in Order_idlist:
            Order_idlist.append(employee.Order_id)

    except Exception as e:
        traceback.print_exc()
        print(f"Error handling row {row_id}: {e}")

async def process_data(request,userid, pan_data, IPOid, OrderType, Groupfilter, IPOTypefilter, InvestorTypefilter, page_number):
    tasks = []
    # Use a set for unique order IDs
    order_ids_set = set()

    # First, collect all Order IDs from the OrderDetail records being updated
    # This ensures we only recalculate what's necessary
    if pan_data:
        affected_od_ids = [int(rid) for rid in pan_data.keys()]
        # Wrapped in sync_to_async for DB call in async function
        def get_order_ids():
            return list(OrderDetail.objects.filter(id__in=affected_od_ids).values_list('Order_id', flat=True))
    
        order_ids = await sync_to_async(get_order_ids)()
        order_ids_set.update(oid for oid in order_ids if oid)

    Order_idlist = list(order_ids_set)

    # PRELOAD CACHES: Pre-fetching clients and IPODetails to avoid N+1 issues
    def preload_caches():
        # Cache for all Clients of this Broker
        c_dict = {c.PANNo.upper().strip(): c for c in ClientDetail.objects.filter(user_id=userid)}
        # Cache for all PANs already allotted in THIS IPO (Mapping PAN -> row_id)
        # Using a dictionary to track which row has which PAN for duplicate detection
        assigned_p_dict = {od.OrderDetailPANNo.PANNo.upper().strip(): od.id 
                           for od in OrderDetail.objects.filter(user_id=userid, Order__OrderIPOName_id=IPOid, Order__OrderType=OrderType).select_related('OrderDetailPANNo') 
                           if od.OrderDetailPANNo}
        return c_dict, assigned_p_dict

    clients_cache, assigned_pans_cache = await sync_to_async(preload_caches)()

    for row_id, data in pan_data.items():
        PAN = data.get('PAN', '').upper().strip()
        clientname = data.get('ClientName', '')
        allotedqty = float(data['AllotedQty']) if data.get('AllotedQty') else None
        DematNo = data.get('DematNumber', '')
        Application = data.get('ApplicationNumber', '')
        rate = data.get('Rate', '')
        # Safely get Pan_Qty, default to None if not present (skipped by frontend)
        Pan_Qty_val = data.get('Pan_Qty', '')
        if Pan_Qty_val != '' and Pan_Qty_val is not None:
            try:
                Pan_Qty = float(Pan_Qty_val)
            except (ValueError, TypeError):
                Pan_Qty = None
        else:
            Pan_Qty = None
        Pan_Demat = data.get('Pan_Demat', '')
        Pan_App = data.get('Pan_App', '')
        Pan_Client = data.get('Pan_Client', '')
    
        # Determine if update is needed based on cache and existing data
        is_changed = False
    
        if PAN == '':
            PAN_id = int(data['PAN_id']) if data.get('PAN_id') else None
            if PAN_id or allotedqty != Pan_Qty or DematNo != Pan_Demat or Application != Pan_App or clientname != Pan_Client:
                task = handle_single_row(userid, PAN, clientname, allotedqty, DematNo, Application, rate, request, row_id, IPOid, OrderType, Groupfilter, IPOTypefilter, InvestorTypefilter, page_number, Order_idlist, clients_cache=clients_cache, assigned_pans_cache=assigned_pans_cache)
                tasks.append(task)
            continue
    
        if PAN != '':
            # Clean the PAN for consistent lookup
            cleaned_pan = re.sub(r'[^A-Za-z0-9]', '', str(PAN)).upper()
        
            # Use preloaded cache instead of individual database filter().first() calls
            client = clients_cache.get(cleaned_pan)
            cq_id = client.id if client else None
        
            # PAN_id passed from frontend check
            PAN_id = int(data['PAN_id']) if data.get('PAN_id') else None
        
            if (PAN_id != cq_id or cq_id is None) or allotedqty != Pan_Qty or DematNo != Pan_Demat or Application != Pan_App or clientname != Pan_Client:
                if cleaned_pan and isValidPAN(cleaned_pan):
                    task = handle_single_row(userid, cleaned_pan, clientname, allotedqty, DematNo, Application, rate, request, row_id, IPOid, OrderType, Groupfilter, IPOTypefilter, InvestorTypefilter, page_number, Order_idlist, clients_cache=clients_cache, assigned_pans_cache=assigned_pans_cache)
                    tasks.append(task)
        
    # All_time = datetime.now()
    if tasks:
        await asyncio.gather(*tasks)
        All_time = datetime.now()
        await sync_to_async(panupload_calculate)(IPOid, userid, Order_idlist)
    
    # for O_id in Order_idlist:
    #     await sync_to_async(calculate)(IPOid, request.user, O_id)


def Update_pann(request,IPOid,OrderType,GrpName=None, OrderCategory=None, InvestorType=None):

    try:
        if request.user.groups.all()[0].name == 'Broker':
            userid = request.user.id
        else:
            userid = request.user.Broker_id
    except:
        userid = request.session[f'link_owner_{IPOid}']
        userid= CustomUser.objects.get(id=userid).id
    # userid = request.user
    pan_data = {}
    page_number = request.GET.get('page','1')
    Groupfilter = unquote(GrpName)
    IPOTypefilter = unquote(OrderCategory)
    InvestorTypefilter = unquote(InvestorType)
    for key, value in request.POST.items():
        if key == 'csrfmiddlewaretoken':
            continue
        
        if key.startswith('PAN_'):
            text_split = key.split('_')
            row_id = text_split[1]
            Rate = text_split[2]
            Pan_id = text_split[3]
            Pan_Qty = text_split[4]
            Pan_Demat = text_split[5]
            Pan_App = text_split[6]
            Pan_Client = text_split[7]
            if row_id:
                pan_data[row_id] = {
                'PAN': value.upper(),  
                'Rate': Rate,
                'PAN_id': Pan_id,
                'Pan_Qty': Pan_Qty,
                'Pan_Demat': Pan_Demat,
                'Pan_App': Pan_App,
                'Pan_Client': Pan_Client,
            }
        
        if key.startswith('allotedqty_'):
            row_id = key.split('_')[1]
            if row_id not in pan_data:
                pan_data[row_id] = {}
            
            pan_data[row_id]['AllotedQty'] = value if value else ''
        
        if key.startswith('DematNo_'):
            row_id = key.split('_')[1]
            if row_id not in pan_data:
                pan_data[row_id] = {}
            
            pan_data[row_id]['DematNumber'] = value if value else ''
        
        if key.startswith('clientname_'):
            row_id = key.split('_')[1]
            if row_id not in pan_data:
                pan_data[row_id] = {}
            
            pan_data[row_id]['ClientName'] = value if value else ''
        
        if key.startswith('Application_'):
            row_id = key.split('_')[1]
            if row_id not in pan_data:
                pan_data[row_id] = {}
            
            pan_data[row_id]['ApplicationNumber'] = value if value else ''


    asyncio.run(process_data(request,userid, pan_data, IPOid, OrderType, Groupfilter, IPOTypefilter, InvestorTypefilter, page_number))

    if request.user.is_authenticated:    
        return redirect(f"/{IPOid}/OrderDetail/{OrderType}/{Groupfilter}/{IPOTypefilter}/{InvestorTypefilter}?page={page_number}")
    else:
        print("User are Unauthenticated")
        linkid = request.session[f'access']
        return redirect(f'/access-link/{linkid}/{OrderType}?page={page_number}')


def ClearSelectedRecords(request):
    """
    Surgically clear database fields for selected OrderDetail records.
    """
    if request.method == "POST":
        row_ids = request.POST.getlist('row_ids[]')
        ipo_id = request.POST.get('IPOid')
    
        if not row_ids:
            return JsonResponse({'status': 'error', 'message': 'No records selected.'}, status=400)
        
        # Determine the user ID correctly, following pattern in Update_pann
        try:
            if request.user.is_authenticated:
                # Optimized group check
                if request.user.groups.filter(name='Broker').exists():
                    userid = request.user.id
                else:
                    userid = request.user.Broker_id
            else:
                # Shared link logic
                link_owner_id = request.session.get(f'link_owner_{ipo_id}')
                if link_owner_id:
                    userid = link_owner_id
                else:
                    return JsonResponse({'status': 'error', 'message': 'Unauthorized: Session expired or invalid.'}, status=401)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Auth Error: {str(e)}'}, status=401)

        try:
            # Fetch the records to clear, matching the exact user ownership
            records = OrderDetail.objects.filter(id__in=row_ids, user_id=userid)
        
            if not records.exists():
                return JsonResponse({'status': 'error', 'message': 'No records found matching your selection.'}, status=404)

            # Identify unique parent orders that might need recalculation
            order_ids = list(records.values_list('Order_id', flat=True).distinct())
        
            # Clear fields: PAN relation, Allotted Qty, Demat, Application and current row Amount
            affected_count = records.update(
                OrderDetailPANNo_id=None,
                AllotedQty=None,
                DematNumber='',
                ApplicationNumber='',
                Amount=0
            )
        
            # Recalculate totals for all affected orders
            for oid in order_ids:
                try:
                    calculate(ipo_id, userid, oid)
                except Exception as calc_err:
                    print(f"Recalculate error for Order {oid}: {calc_err}")
            
            return JsonResponse({
                'status': 'success', 
                'message': f'Successfully cleared {affected_count} records.'
            })
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': f'Database Update Error: {str(e)}'}, status=500)
        
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)


# app-buy and sell order details add pan or update fun
@allowed_users(allowed_roles=['Broker', 'Customer'])
def AddPan(request, OrderDetailId, IPOid, OrderType, GrpName=None, OrderCategory=None, InvestorType=None, OrderDate=None, OrderTime=None):
    if request.user.groups.all()[0].name == 'Broker':
        userid = request.user
    else:
        userid = request.user.Broker_id
    employee = OrderDetail.objects.get(user=userid, id=OrderDetailId)

    IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)
    PAN = request.POST.get('PAN', '').upper()
    clientname = request.POST.get('clientname', '')
    allotedqty = request.POST.get('allotedqty', '')
    Application = request.POST.get('Application', '')
    DematNo = request.POST.get('DematNo', '')
    Groupfilter = request.POST.get('Groupfilter', '')
    IPOTypefilter = request.POST.get('IPOTypefilter', '')
    InvestorTypeFilter = request.POST.get('InvestorTypeFilter', '')
    if request.method == "POST":
        rate ="{:.0f}".format(employee.Order.Rate)

        if PAN == '':
            employee.OrderDetailPANNo_id = None
            employee.AllotedQty = None
            employee.DematNumber = ''
            employee.ApplicationNumber = ''
            employee.save()
            return redirect(f"/{IPOid}/OrderDetail/{OrderType}/{GrpName}/{OrderCategory}/{InvestorType}/{OrderDate}/{OrderTime}")

        elif not isValidPAN(PAN):
            messages.error(request, f"Row ['{employee.Order.OrderGroup}','{employee.Order.OrderCategory}','{employee.Order.InvestorType}','{rate}','{PAN}','{clientname}','{allotedqty}','{DematNo}','{Application}', 'Invalid PAN'] has Invalid PAN No.")
            return redirect(f"/{IPOid}/OrderDetail/{OrderType}/{GrpName}/{OrderCategory}/{InvestorType}/{OrderDate}/{OrderTime}")     
    
        elif PAN != '':
            query = ClientDetail.objects.filter(PANNo=PAN.upper(), user=userid)
            if query.exists():
                query1 = ClientDetail.objects.get(PANNo=PAN.upper(), user=userid)
                if employee.Order.OrderGroup == query1.Group:
                    pass
                else:
                    query1.Group = employee.Order.OrderGroup
                query1.Name = clientname
                query1.save()
            else:
                PANNUMBER = ClientDetail(user=userid, PANNo=PAN.upper(), Name=clientname, Group=employee.Order.OrderGroup)
                PANNUMBER.save()
            r = 1
            query2 = ClientDetail.objects.get(
                PANNo=PAN.upper(), user=userid)
            for j in OrderDetail.objects.filter(user=userid, Order__OrderIPOName_id=IPOid, Order__OrderType=OrderType).values('OrderDetailPANNo__PANNo'):
                if PAN.upper() == j.get('OrderDetailPANNo__PANNo'):
                    if employee.OrderDetailPANNo_id != query2.id:
                        messages.error(request, f"Row ['{employee.Order.OrderGroup}','{employee.Order.OrderCategory}','{employee.Order.InvestorType}','{rate}','{PAN}','{clientname}','{allotedqty}','{DematNo}','{Application}', 'Pan_exist_already'] has PAN no. that already exists.")
                
                        r = 0
                        break

            if r == 1:
                panno = ClientDetail.objects.get(PANNo=PAN.upper(), user=userid)
                employee.OrderDetailPANNo_id = panno.id
                if allotedqty == '':
                    employee.AllotedQty = None
                else:
                    employee.AllotedQty = allotedqty
                employee.DematNumber = DematNo
                employee.ApplicationNumber = Application
                employee.save()
                calculate(IPOid, request.user,employee.Order_id)
            
        else:
            pass
    return redirect(f"/{IPOid}/OrderDetail/{OrderType}/{GrpName}/{OrderCategory}/{InvestorType}/{OrderDate}/{OrderTime}")

@allowed_users(allowed_roles=['Broker', 'Customer'])
def FirmAllotment(request, IPOid, OrderType, GrpName, OrderCategory, InvestorType, Rate='All'):
    if request.user.groups.all()[0].name == 'Broker':
        userid = request.user
    else:
        userid = request.user.Broker_id
    IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)

    if request.method == "POST":
        AllotedQtyv = request.POST.get('AllotedQty', '')
        Group = request.POST.get('Group', '')
        if IPOName.IPOType == "MAINBOARD":
            InvestorTypeFilter = request.POST.get('InvestorType', '')
        else:
            InvestorTypeFilter = "All"

        if AllotedQtyv != '' or AllotedQtyv == '':
        
            if Group=='All' and InvestorTypeFilter=="All":
                j = OrderDetail.objects.filter(user=userid, Order__OrderIPOName_id=IPOid, Order__OrderType=OrderType)
        
            elif Group=='All':
                j = OrderDetail.objects.filter(user=userid, Order__OrderIPOName_id=IPOid, Order__OrderType=OrderType, Order__InvestorType=InvestorTypeFilter )
        
            elif InvestorTypeFilter=='All': 
                gid = GroupDetail.objects.get(GroupName=Group, user=userid).id  
                j = OrderDetail.objects.filter(user=userid, Order__OrderIPOName_id=IPOid, Order__OrderType=OrderType, Order__OrderGroup_id=gid)
        
            else:
                gid = GroupDetail.objects.get(GroupName=Group, user=userid).id  
                j = OrderDetail.objects.filter(user=userid, Order__OrderIPOName_id=IPOid, Order__OrderType=OrderType, Order__OrderGroup_id=gid, Order__InvestorType=InvestorTypeFilter)

            if j.exists():
                if AllotedQtyv == '':
                    j.update(AllotedQty=None)  # clear the allotment
                else:
                    j.update(AllotedQty=AllotedQtyv)
            
                calculate(IPOid, request.user)
        
    if GrpName == 'None' and OrderCategory == 'None' and InvestorType == 'None':
        return redirect(f"/{IPOid}/OrderDetail/{OrderType}")
    return redirect(f"/{IPOid}/OrderDetail/{OrderType}/{GrpName}/{OrderCategory}/{InvestorType}")

#client wise billing fun
@allowed_users(allowed_roles=['Broker', 'Customer'])
def Billing(request, IPOid):
    if request.user.groups.all()[0].name == 'Broker':
        userid = request.user
        # entry = OrderDetail.objects.filter(
        #     user=userid, Order__OrderIPOName_id=IPOid)
        entry = (OrderDetail.objects.filter(
            user=userid, Order__OrderIPOName_id=IPOid)
            .values(
            "id",
            "Amount",
            "PreOpenPrice",
            "AllotedQty",
            "Order__OrderGroup__GroupName",
            "Order__OrderCategory",
            "Order__InvestorType",
            "Order__OrderType",
            "Order__Rate",
            "Order__Method",
            "OrderDetailPANNo__PANNo",
            "Order__remark",
        ))
        Group = GroupDetail.objects.filter(user=userid)
    else:
        userid = request.user.Broker_id
        entry = OrderDetail.objects.filter(
            user=userid, Order__OrderIPOName_id=IPOid, Order__OrderGroup_id=request.user.Group_id)
        Group = GroupDetail.objects.filter(
            user=userid, id=request.user.Group_id)
    IPO = CurrentIpoName.objects.get(id=IPOid, user=userid)
    total = 0

    # IPO_Name = CurrentIpoName.objects.get(id=IPOid, user=userid)
    # IpoName = IPO_Name.IPOName

    # orderpreopen = OrderDetail.objects.filter(Order__OrderIPOName_id=IPOid, user=request.user, PreOpenPrice=0)
    # orderpreopen.update(PreOpenPrice = IPO_Name.PreOpenPrice)

    IPOName = IPO

    order = Order.objects.filter(
            user=userid,
            OrderIPOName_id=IPOid
        ).filter(
            Q(OrderCategory="Premium") | Q(OrderCategory="CALL") | Q(OrderCategory="PUT")
        ).select_related('OrderGroup')


    Total1 = order.aggregate(Sum('Amount'))
    Total = Total1['Amount__sum']
    if Total == None:
        Total = 0
    else:
        Total = Total
    totalorder = total + Total
    Total1 = entry.aggregate(Sum('Amount'))
    Total = Total1['Amount__sum']
    if Total == None:
        Total = 0
    total = total + Total
    total = total + totalorder

    IPOTypefilterList = {'Kostak', 'Subject To','CALL','PUT','Premium',}
    InvestorTypeFilterList = {'RETAIL','SHNI','BHNI','OPTIONS','PREMIUM'}
    Groupfilter = 'All'
    IPOTypefilter = 'All'
    InvestorTypeFilter = 'All'

    if request.method == "POST":
        Groupfilter = request.POST.get('Groupfilter', '')
        IPOTypefilter = request.POST.get('IPOTypefilter', '')
        InvestorTypeFilter = request.POST.get('InvestorTypeFilter', '')
    
        if Groupfilter == '' and IPOTypefilter == '' and  InvestorTypeFilter == '' :
            Groupfilter = 'All'
            IPOTypefilter = 'All'
            InvestorTypeFilter = 'All'
    
        total = 0
        if is_valid_queryparam(Groupfilter) and Groupfilter != 'All':
            gid = GroupDetail.objects.get(
                GroupName=Groupfilter, user=userid).id
            entry = entry.filter(Order__OrderGroup_id=gid)
            order = order.filter(OrderGroup_id=gid)
        if is_valid_queryparam(IPOTypefilter) and IPOTypefilter != 'All':
            entry = entry.filter(Order__OrderCategory=IPOTypefilter)
            order = order.filter(OrderCategory=IPOTypefilter)
        if is_valid_queryparam(InvestorTypeFilter) and InvestorTypeFilter != 'All':
            entry = entry.filter(Order__InvestorType=InvestorTypeFilter)
            order = order.filter(InvestorType=InvestorTypeFilter)
        Total1 = order.aggregate(Sum('Amount'))
        Total = Total1['Amount__sum']
        if Total == None:
            Total = 0
        else:
            Total = Total
        totalorder = total + Total
        Total1 = entry.aggregate(Sum('Amount'))
        Total = Total1['Amount__sum']
        if Total == None:
            Total = 0
        total = total + Total
        total = total + totalorder
    
    page_obj = None
    try:
        page_size = request.POST.get('Billing_page_size')
        if page_size != '' and page_size != None:
            request.session['Billing_page_size'] = page_size
        else:
            page_size = request.session['Billing_page_size']
    except:
        page_size = request.session.get('Billing_page_size', 50)
    

    Data = []

    entry_count = entry.count() if entry else 0
    order_count = order.count() if order else 0
    total_count = entry_count + order_count

    # If no records, render a friendly empty table and avoid pagination errors

   
    # display_page_size  = page_size if page_size != 'All' else total_count
    if page_size == 'All' or not page_size:
        display_page_size = max(total_count, 1)  # never zero
    else:
        try:
            display_page_size = int(page_size)
        except:
            display_page_size = 50
        if display_page_size <= 0:
            display_page_size = 50
    paginator = Paginator(range(total_count), display_page_size)

    # Get current page number and calculate start/end indices safely
    page_number = request.GET.get('page','1')
    page_obj = paginator.get_page(page_number)
    start_index_raw = page_obj.start_index() - 1
    start_index = 0 if start_index_raw < 0 else start_index_raw
    end_index = page_obj.end_index()
    if end_index is None:
        end_index = 0

    entry_total_amount = 0

    if start_index < entry_count:
        if entry_count != 0 :
            entry_end = min(end_index, entry_count)
            entry_page_data = entry[start_index:entry_end]
    
            # for order_detail in entry_page_data:
            #     entry_toatal_amount = entry_toatal_amount + order_detail.Amount
            #     entry_data = {
            #         'id':order_detail.id,
            #         'OrderGroup': order_detail.Order.OrderGroup,
            #         'OrderCategory': order_detail.Order.OrderCategory,
            #         'InvestorType': order_detail.Order.InvestorType,
            #         'OrderType': order_detail.Order.OrderType,
            #         'Rate': order_detail.Order.Rate,
            #         'Method': order_detail.Order.Method,
            #         'PANNo': order_detail.OrderDetailPANNo.PANNo if (order_detail.OrderDetailPANNo and order_detail.OrderDetailPANNo.PANNo is not None) else '',   
            #         'PreOpenPrice': order_detail.PreOpenPrice ,
            #         'AllotedQty': float(order_detail.AllotedQty) if (order_detail.AllotedQty is not None) else '',
            #         'Amount': order_detail.Amount,
            #         # Add other fields as needed
            #     }
            #     Data.append(entry_data)
            entry_total_amount = 0
            Data = []

            for row in entry_page_data:
                print(row)
                entry_total_amount += row["Amount"]

                entry_data = {
                    "id": row["id"],
                    "OrderGroup": row["Order__OrderGroup__GroupName"],
                    "OrderCategory": row["Order__OrderCategory"],
                    "InvestorType": row["Order__InvestorType"],
                    "OrderType": row["Order__OrderType"],
                    "Rate": row["Order__Rate"],
                    "Method": row["Order__Method"],
                    "PANNo": row["OrderDetailPANNo__PANNo"] or "",
                    "PreOpenPrice": row["PreOpenPrice"],
                    "AllotedQty": float(row["AllotedQty"]) if row["AllotedQty"] is not None else "",
                    "Amount": row["Amount"],
                    "Remark": format_remark(row["Order__remark"]) or "-",
                }
                Data.append(entry_data)
        
    if end_index > entry_count:
        if order_count != 0 :
            order_start = max(0, start_index - order_count)
            order_end = end_index - entry_count
            order_page_data = order[order_start:order_end]

            for order_detail in order_page_data:
                entry_total_amount = entry_total_amount + order_detail.Amount
                order_data = {
                    'id':order_detail.id,
                    'OrderGroup': order_detail.OrderGroup,
                    'OrderCategory': order_detail.OrderCategory,
                    'InvestorType': order_detail.InvestorType,
                    'OrderType': order_detail.OrderType,
                    'Rate': order_detail.Rate,
                    'Method': order_detail.Method,
                    'PANNo': '-',   
                    'PreOpenPrice': IPO.PreOpenPrice,
                    'AllotedQty': float(order_detail.Quantity),
                    'Amount': order_detail.Amount,
                    'Remark': format_remark(order_detail.remark) or "-",
                }
                Data.append(order_data)

    # if Data:
    # if entry is not None and entry.exists():
    df = pd.DataFrame.from_records(Data)
    if "InvestorType" in df.columns:
        df = df.sort_values(by="InvestorType", key=lambda x: x == "PREMIUM").reset_index(drop=True)
    html_table = "<table >\n"
    html_table = "<thead><tr style='text-align: center;'>"
    html_table += "<th><input type='checkbox' id='select-all-billing'></th>"
    html_table += "<th>Group</th>"
    html_table += "<th>Order Category</th>"
    html_table += "<th>Premium Strike Price</th>"
    if IPOName.IPOType == "MAINBOARD":
        html_table += "<th>Investor Type</th>"
    html_table += "<th>Order Type</th>"
    html_table += "<th>Rate</th>"
    html_table += "<th>PAN No</th>"
    html_table += "<th>Pre-Open Price</th>"
    html_table += "<th>Alloted Qty</th>"
    html_table += "<th class='remark-col'>Remark</th>"
    html_table += "<th>Amount</th>"
    html_table += "</tr></thead>\n"
    # Add rows
    float_format = "{:.0f}"
    html_table += "<tbody style='text-align: center;white-space: nowrap;'>"
    for i, row in df.iterrows():
        html_table += "<tr style='text-align: center;'>"
        html_table += f"<td><input type='checkbox' class='billing-row-checkbox' value='{row.id}'></td>"
        html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','{row.OrderGroup}','All','All')\" title=\"Double-click to filter by this Group\">{row.OrderGroup}</td>"
        html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','All','{row.OrderCategory}','All')\" title=\"Double-click to filter by this Order Category\">{row.OrderCategory}</td>"
        if row.OrderCategory != 'Premium':
            method = row.Method if row.Method else 'Application'
            html_table += f"<td>{method}</td>"
        else:
            html_table += f"<td>-</td>"
        if not pd.isna(row.id):
            row_id = int(row.id)
        else:
            row_id = None
        
        if IPOName.IPOType == "MAINBOARD":
            action_url = f'/{IPOid}/{row_id}/EditOrderPreOpenPrice/{row.OrderCategory}/{row.InvestorType}/{Groupfilter}/{IPOTypefilter}/{InvestorTypeFilter}?page={page_number}'
            html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','All','All','{row.InvestorType}')\" title=\"Double-click to filter by this Investor Type\">{row.InvestorType}</td>"
        else:
            action_url = f'/{IPOid}/{ row_id}/EditOrderPreOpenPrice/{row.OrderCategory}/{row.InvestorType}/{Groupfilter}/{IPOTypefilter}/All?page={page_number}'
        
        html_table += f"<td>{row.OrderType}</td>"
        html_table += f"<td>{row.Rate}</td>"
        html_table += f"<td>{row.PANNo}</td>"
        pre_open_price = row.PreOpenPrice if row.PreOpenPrice != 0.0 else IPO.PreOpenPrice
        if row.OrderCategory != 'Premium' and row.InvestorType != 'OPTIONS':
            html_table += f"<td><a href='#' style='color: #007bff;' data-id='{row.id}' data-preopen-price='{pre_open_price}' data-action-url='{action_url}' data-toggle='modal' data-target='#edit-modal'> {pre_open_price} </a></td>"
        else:
            html_table += f"<td>{pre_open_price}</td>"
        
        try:
            qty_val = float(row.AllotedQty)
            formatted_qty = float_format.format(qty_val)
        except (ValueError, TypeError):
            formatted_qty = row.AllotedQty
        html_table += f"<td>{formatted_qty}</td>"
     
        safe_remark = row.Remark.replace("'", "\\'").replace('"', '&quot;') if row.Remark else ""
        html_table += f"<td style='white-space: nowrap; max-width: 300px; overflow: hidden; text-overflow: ellipsis; cursor: pointer; outline: none;' tabindex='0' onclick=\"this.style.whiteSpace=this.style.whiteSpace==='normal'?'nowrap':'normal'\" onblur=\"this.style.whiteSpace='nowrap'\" title='{safe_remark}'>{row.Remark}</td>"

        try:
            amt_val = float(row.Amount)
            formatted_amt = float_format.format(amt_val)
        except (ValueError, TypeError):
            formatted_amt = row.Amount
        html_table += f"<td>{formatted_amt}</td>"
        html_table += "</tr>\n"
    
    html_table += "</tbody>"
    html_table += "<tfoot><tr>"
    html_table += "<th>Total</th>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    if IPOName.IPOType == "MAINBOARD":
        html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += f"<th style='text-align: center;'>{float_format.format(entry_total_amount)}</th>"
    html_table += "</tr></tfoot>"
    html_table += "</table>"

    # if entry is not None and entry.exists():
    #     for i, row in df.iterrows():
    #         pre_open_price = row.PreOpenPrice if row.PreOpenPrice != 0.0 else IPO.PreOpenPrice
    #         csrf_token = csrf.get_token(request)
        
    #         if not pd.isna(row.id):
    #             row_id = int(row.id)
    #         else:
    #             row_id = None
    #         if IPOName.IPOType == "MAINBOARD":
    #             action_url = f'/{IPOid}/{ row_id }/EditOrderPreOpenPrice/{row.OrderCategory}/{row.InvestorType}/{Groupfilter}/{IPOTypefilter}/{InvestorTypeFilter}'
    #         else:
    #             action_url = f'/{IPOid}/{ row_id }/EditOrderPreOpenPrice/{row.OrderCategory}/{row.InvestorType}/{Groupfilter}/{IPOTypefilter}/All'
            
            
    #         html_table += f"""
    #             <div class="modal fade" id="edit-{ row.id }" tabindex="-1" role="dialog" aria-labelledby="exampleModalLabels"
    #                 aria-hidden="true">
    #                 <div class="modal-dialog" role="document">
    #                     <div class="modal-content">
    #                         <div class="modal-header" style="border-bottom: 1px solid black;">
    #                             <h5 class="modal-title" id="exampleModalLabels">Pre-Open Price Edit</h5>
    #                             <button type="button" class="close" data-dismiss="modal" aria-label="Close">
    #                                 <span aria-hidden="true">&times;</span>
    #                             </button>
    #                         </div>
    #                         <div class="modal-body" style="border-bottom: 1px solid black;">
    #                             <form action="{action_url}"  method="POST"
    #                                 enctype="multipart/form-data" style="margin: 15px 22px;" class="need-validation"
    #                                 novalidate>
                                
    #                                 <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
    #                                 <label for="category"><b>PreOpenPrice : </b></label>
    #                                 <input type="text" value="{pre_open_price}" name="PreOpenPrice"
    #                                     oninput="this.value = this.value.replace(/[^0-9.]/g, '').replace(/(\..?)\../g, '$1');" / style="height: 37px;">
    #                                 <button type="submit" class="btn btn-outline-primary">Submit</button>
    #                             </form>
    #                         </div>
    #                     </div>
    #                 </div>
    #             </div> 
    #         """

    return render(request, 'Billing.html', {'Group': Group.order_by('GroupName'),'html_table':html_table,'select': IPOTypefilterList, 'select2': InvestorTypeFilterList,"total": "{:.0f}".format(total),'Groupfilter': Groupfilter, "IPOName": IPO, 'IPOTypefilter': IPOTypefilter, 'InvestorTypeFilter': InvestorTypeFilter,  "IPO": IPO, "IPOid": IPOid,'page_obj': page_obj,'Billing_page_size':page_size})
    return render(request, 'Billing.html', {'Group': Group.order_by('GroupName'),'select': IPOTypefilterList, 'select2': InvestorTypeFilterList,"total": "{:.0f}".format(total),'Groupfilter': Groupfilter, "IPOName": IPO, 'IPOTypefilter': IPOTypefilter, 'InvestorTypeFilter': InvestorTypeFilter,  "IPO": IPO, "IPOid": IPOid,'page_obj': page_obj,'Billing_page_size':page_size})

def FileterBilling(request, IPOid ,group,IPOType,InvestType, Rate='All'):
    if request.user.groups.all()[0].name == 'Broker':
        userid = request.user
        entry = (OrderDetail.objects.filter(
            user=userid, Order__OrderIPOName_id=IPOid)
            .values(
            "id",
            "Amount",
            "PreOpenPrice",
            "AllotedQty",
            "Order__OrderGroup__GroupName",
            "Order__OrderCategory",
            "Order__InvestorType",
            "Order__OrderType",
            "Order__Rate",
            "Order__Method",
            "OrderDetailPANNo__PANNo",
            "Order__remark"
        ))
        Group = GroupDetail.objects.filter(user=userid)
    else:
        userid = request.user.Broker_id
        entry = OrderDetail.objects.filter(
            user=userid, Order__OrderIPOName_id=IPOid, Order__OrderGroup_id=request.user.Group_id)
        Group = GroupDetail.objects.filter(
            user=userid, id=request.user.Group_id)
    Groupfilter = unquote(group)
    IPOTypefilter = unquote(IPOType)
    InvestorTypeFilter = unquote(InvestType)
 
    IPO = CurrentIpoName.objects.get(id=IPOid, user=userid)
    total = 0

    IPO_Name = IPO
    # IpoName = IPO_Name.IPOName

    orderpreopen = OrderDetail.objects.filter(Order__OrderIPOName_id=IPOid, user=request.user, PreOpenPrice=0)
    orderpreopen.update(PreOpenPrice = IPO_Name.PreOpenPrice)

    IPOName = IPO

    # order = Order.objects.filter(
    #     user=userid, OrderIPOName_id=IPOid, OrderCategory="Premium")

    order = Order.objects.filter(
            user=userid,
            OrderIPOName_id=IPOid
        ).filter(
            Q(OrderCategory="Premium") | Q(OrderCategory="CALL") | Q(OrderCategory="PUT")
        ).select_related('OrderGroup')

    IPOTypefilterList = {'Kostak', 'Subject To','CALL','PUT','Premium'}
    InvestorTypeFilterList = {'RETAIL','SHNI','BHNI','OPTIONS','PREMIUM'}

    total = 0
    if is_valid_queryparam(Groupfilter) and Groupfilter != 'All':
        gid = GroupDetail.objects.get(
            GroupName=Groupfilter, user=userid).id
        entry = entry.filter(Order__OrderGroup_id=gid)
        order = order.filter(OrderGroup_id=gid)
    if is_valid_queryparam(IPOTypefilter) and IPOTypefilter != 'All':
        entry = entry.filter(Order__OrderCategory=IPOTypefilter)
        order = order.filter(OrderCategory=IPOTypefilter)
    if is_valid_queryparam(InvestorTypeFilter) and InvestorTypeFilter != 'All':
        entry = entry.filter(Order__InvestorType=InvestorTypeFilter)
        order = order.filter(InvestorType=InvestorTypeFilter)
    Total1 = order.aggregate(Sum('Amount'))
    Total = Total1['Amount__sum']
    if Total == None:
        Total = 0
    else:
        Total = Total
    totalorder = total + Total
    Total1 = entry.aggregate(Sum('Amount'))
    Total = Total1['Amount__sum']
    if Total == None:
        Total = 0
    total = total + Total
    total = total + totalorder

    page_obj = None
    try:
        page_size = request.POST.get('Billing_page_size')
        if page_size != '' and page_size != None:
            request.session['Billing_page_size'] = page_size
        else:
            page_size = request.session['Billing_page_size']
    except:
        page_size = request.session.get('Billing_page_size', 50)
    

    Data = []

    entry_total_amount = 0

    entry_count = entry.count() if entry else 0
    order_count = order.count() if order else 0
    total_count = entry_count + order_count

    # page_size = page_size if page_size != 'All' else total_count
    # Safe per-page calculation (never 0)
    if page_size == 'All':
        display_page_size = total_count if total_count > 0 else 1
    else:
        try:
            display_page_size = int(page_size)
        except Exception:
            display_page_size = 50
        if display_page_size <= 0:
            display_page_size = 1

    paginator = Paginator(range(total_count), display_page_size)

    # Get current page number and calculate start/end indices
    page_number = request.GET.get('page','1')
    page_obj = paginator.get_page(page_number)
    start_index = page_obj.start_index() - 1
    end_index = page_obj.end_index()
    if start_index < entry_count:
        if entry_count != 0 :
            entry_end = min(end_index, entry_count)
            entry_page_data = entry[start_index:entry_end]
        
        # for order_detail in entry_page_data:
        #     entry_toatal_amount = entry_toatal_amount + order_detail.Amount
        #     entry_data = {
        #         'id':order_detail.id,
        #         'OrderGroup': order_detail.Order.OrderGroup,
        #         'OrderCategory': order_detail.Order.OrderCategory,
        #         'InvestorType': order_detail.Order.InvestorType,
        #         'OrderType': order_detail.Order.OrderType,
        #         'Rate': order_detail.Order.Rate,
        #         'Method': order_detail.Order.Method,
        #         'PANNo': order_detail.OrderDetailPANNo.PANNo if (order_detail.OrderDetailPANNo and order_detail.OrderDetailPANNo.PANNo is not None) else '',   
        #         'PreOpenPrice': order_detail.PreOpenPrice ,
        #         'AllotedQty': float(order_detail.AllotedQty) if (order_detail.AllotedQty is not None) else '',
        #         'Amount': order_detail.Amount,
        #     }
        #     Data.append(entry_data)
        entry_total_amount = 0
        Data = []

        for row in entry_page_data:
            entry_total_amount += row["Amount"]

            entry_data = {
                "id": row["id"],
                "OrderGroup": row["Order__OrderGroup__GroupName"],
                "OrderCategory": row["Order__OrderCategory"],
                "InvestorType": row["Order__InvestorType"],
                "OrderType": row["Order__OrderType"],
                "Rate": row["Order__Rate"],
                "Method": row["Order__Method"],
                "PANNo": row["OrderDetailPANNo__PANNo"] or "",
                "PreOpenPrice": row["PreOpenPrice"],
                "AllotedQty": float(row["AllotedQty"]) if row["AllotedQty"] is not None else "",
                "Amount": row["Amount"],
                "Remark": format_remark(row["Order__remark"]) or "-",
            }
            Data.append(entry_data)
    

    if end_index > entry_count:
        if order_count != 0 :
            order_start = max(0, start_index - entry_count)
            order_end = end_index - entry_count
            order_page_data = order[order_start:order_end]

            for order_detail in order_page_data:
                entry_total_amount = entry_total_amount + order_detail.Amount
                order_data = {
                    'id':order_detail.id,
                    'OrderGroup': order_detail.OrderGroup,
                    'OrderCategory': order_detail.OrderCategory,
                    'InvestorType': order_detail.InvestorType,
                    'OrderType': order_detail.OrderType,
                    'Rate': order_detail.Rate,
                    'Method': order_detail.Method,
                    'PANNo': '-',   
                    'PreOpenPrice': IPO.PreOpenPrice,
                    'AllotedQty': float(order_detail.Quantity),
                    'Amount': order_detail.Amount,
                    'Remark': format_remark(order_detail.remark) or "-",
                }
                Data.append(order_data)
        
    df = pd.DataFrame.from_records(Data)
    if "InvestorType" in df.columns:
        df = df.sort_values(by="InvestorType", key=lambda x: x == "PREMIUM").reset_index(drop=True)
    html_table = "<table >\n"
    html_table = "<thead><tr style='text-align: center;'>"
    html_table += "<th><input type='checkbox' id='select-all-billing'></th>"
    html_table += "<th>Group</th>"
    html_table += "<th>Order Category</th>"
    html_table += "<th>Premium Strike Price</th>"
    if IPOName.IPOType == "MAINBOARD":
        html_table += "<th>Investor Type</th>"
    html_table += "<th>Order Type</th>"
    html_table += "<th>Rate</th>"
    html_table += "<th>PAN No</th>"
    html_table += "<th>Pre-Open Price</th>"
    html_table += "<th>Alloted Qty</th>"
    html_table += "<th class='remark-col'>Remark</th>"
    html_table += "<th>Amount</th>"
    html_table += "</tr></thead>\n"
    # Add rows
    float_format = "{:.0f}"
    html_table += "<tbody style='text-align: center;white-space: nowrap;'>"
    if len(df) == 0:
        column_count = 10 + (1 if IPOName.IPOType == "MAINBOARD" else 0)
        html_table += f"<tr class='odd'><td colspan='{column_count}' valign='top' class='dataTables_empty'>No data available</td></tr>"
    for i, row in df.iterrows():
        html_table += "<tr style='text-align: center;'>"
        html_table += f"<td><input type='checkbox' class='billing-row-checkbox' value='{row.id}'></td>"
        html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','{row.OrderGroup}','All','All')\" title=\"Double-click to filter by this Group\">{row.OrderGroup}</td>"
        html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','All','{row.OrderCategory}','All')\" title=\"Double-click to filter by this Order Category\">{row.OrderCategory}</td>"
        if row.OrderCategory != 'Premium':
            method = row.Method if row.Method else 'Application'
            html_table += f"<td>{method}</td>"
        else:
            html_table += f"<td>-</td>"
        if not pd.isna(row.id):
            row_id = int(row.id)
        else:
            row_id = None
        
        if IPOName.IPOType == "MAINBOARD":
            action_url = f'/{IPOid}/{row_id}/EditOrderPreOpenPrice/{row.OrderCategory}/{row.InvestorType}/{Groupfilter}/{IPOTypefilter}/{InvestorTypeFilter}?page={page_number}'
            html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','All','All','{row.InvestorType}')\" title=\"Double-click to filter by this Investor Type\">{row.InvestorType}</td>"
        else:
            action_url = f'/{IPOid}/{ row_id}/EditOrderPreOpenPrice/{row.OrderCategory}/{row.InvestorType}/{Groupfilter}/{IPOTypefilter}/All?page={page_number}'
        
        html_table += f"<td>{row.OrderType}</td>"
        html_table += f"<td>{row.Rate}</td>"
        html_table += f"<td>{row.PANNo}</td>"
        pre_open_price = row.PreOpenPrice if row.PreOpenPrice != 0.0 else IPO.PreOpenPrice
        if row.OrderCategory != 'Premium' and row.InvestorType != 'OPTIONS':
            html_table += f"<td><a href='#' style='color: #007bff;' data-id='{row.id}' data-preopen-price='{pre_open_price}' data-action-url='{action_url}' data-toggle='modal' data-target='#edit-modal'> {pre_open_price} </a></td>"
        else:
            html_table += f"<td>{pre_open_price}</td>"
        
        safe_alloted_qty = float(row.AllotedQty) if pd.notna(row.AllotedQty) and row.AllotedQty != '' else 0.0
        html_table += f"<td>{float_format.format(safe_alloted_qty)}</td>"
     
        safe_remark = row.Remark.replace("'", "\\'").replace('"', '&quot;') if row.Remark else ""
        html_table += f"<td style='white-space: nowrap; max-width: 300px; overflow: hidden; text-overflow: ellipsis; cursor: pointer; outline: none;' tabindex='0' onclick=\"this.style.whiteSpace=this.style.whiteSpace==='normal'?'nowrap':'normal'\" onblur=\"this.style.whiteSpace='nowrap'\" title='{safe_remark}'>{row.Remark}</td>"

        safe_amount = float(row.Amount) if pd.notna(row.Amount) and row.Amount != '' else 0.0
        html_table += f"<td>{float_format.format(safe_amount)}</td>"
        html_table += "</tr>\n"
    html_table += "</tbody>"
    html_table += "<tfoot><tr>"
    html_table += "<th>Total</th>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    if IPOName.IPOType == "MAINBOARD":
        html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    html_table += "<td style='text-align: center;'></td>"
    safe_entry_total = float(entry_total_amount) if pd.notna(entry_total_amount) and entry_total_amount != '' else 0.0
    html_table += f"<th style='text-align: center;'>{float_format.format(safe_entry_total)}</th>"

    html_table += "</tr></tfoot>"
    html_table += "</table>"
    
        # for i, row in df.iterrows():
        #     pre_open_price = row.PreOpenPrice if row.PreOpenPrice != 0.0 else IPO.PreOpenPrice
        #     csrf_token = csrf.get_token(request)
        
        #     if not pd.isna(row.id):
        #         row_id = int(row.id)
        #     else:
        #         row_id = None
            
        #     if IPOName.IPOType == "MAINBOARD":
        #         action_url = f'/{IPOid}/{ row_id }/EditOrderPreOpenPrice/{row.OrderCategory}/{row.InvestorType}/{Groupfilter}/{IPOTypefilter}/{InvestorTypeFilter}'
        #     else:
        #         action_url = f'/{IPOid}/{ row_id }/EditOrderPreOpenPrice/{row.OrderCategory}/{row.InvestorType}/{Groupfilter}/{IPOTypefilter}/All'
            
        #     html_table += f"""
        #         <div class="modal fade" id="edit-{ row.id }" tabindex="-1" role="dialog" aria-labelledby="exampleModalLabels"
        #             aria-hidden="true">
        #             <div class="modal-dialog" role="document">
        #                 <div class="modal-content">
        #                     <div class="modal-header" style="border-bottom: 1px solid black;">
        #                         <h5 class="modal-title" id="exampleModalLabels">Pre-Open Price Edit</h5>
        #                         <button type="button" class="close" data-dismiss="modal" aria-label="Close">
        #                             <span aria-hidden="true">&times;</span>
        #                         </button>
        #                     </div>
        #                     <div class="modal-body" style="border-bottom: 1px solid black;">
        #                         <form action="{action_url}" id="form-id2" method="POST"
        #                             enctype="multipart/form-data" style="margin: 15px 22px;" class="need-validation"
        #                             novalidate>
                                
        #                             <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
        #                             <label for="category"><b>PreOpenPrice : </b></label>
        #                             <input type="text" value="{pre_open_price}" name="PreOpenPrice"
        #                                 oninput="this.value = this.value.replace(/[^0-9.]/g, '').replace(/(\..?)\../g, '$1');" / style="height: 37px;">
        #                             <button type="submit" class="btn btn-outline-primary">Submit</button>
        #                         </form>
        #                     </div>
        #                 </div>
        #             </div>
        #         </div> 
        #     """

    return render(request, 'Billing.html', {'Group': Group,'html_table':html_table,'select': IPOTypefilterList, 'select2': InvestorTypeFilterList,"total": "{:.0f}".format(total),'Groupfilter': Groupfilter, "IPOName": IPO, 'IPOTypefilter': IPOTypefilter, 'InvestorTypeFilter': InvestorTypeFilter,  "IPO": IPO, "IPOid": IPOid,'page_obj': page_obj,'Billing_page_size':page_size})
    # return render(request, 'Billing.html', {'entry': entry, 'order': order, 'Group': Group.order_by('GroupName'), 'select': IPOTypefilterList, 'select2': InvestorTypeFilterList, "total": "{:.0f}".format(total), 'Groupfilter': Groupfilter, "IPOName": IPO, 'IPOTypefilter': IPOTypefilter, 'InvestorTypeFilter': InvestorTypeFilter,  "IPO": IPO, "IPOid": IPOid})

#client wise biling filter wise download fun
@allowed_users(allowed_roles=['Broker'])
def exportBillingFilter(request, IPOid, group=None, IPOType=None, InvestorType=None):
    group = unquote(group)
    IPOType = unquote(IPOType)
    IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)
    response = HttpResponse(content_type='text/csv')
    entry = OrderDetail.objects.filter(
        user=request.user, Order__OrderIPOName=IPOName)
    order = Order.objects.filter(
        user=request.user, OrderIPOName_id=IPOid, OrderCategory="Premium")

    writer = csv.writer(response)
    if IPOName.IPOType == "MAINBOARD":
        writer.writerow(['Group', 'Order Category', 'Investor Type', 'Order Type', 'Rate', 'AllotedQty','Pre-Open Price', 'Amount Difference', 'PAN No',
                    'Client Name'])
    else:
        writer.writerow(['Group', 'Order Category', 'Order Type', 'Rate', 'AllotedQty','Pre-Open Price', 'Amount Difference', 'PAN No',
                    'Client Name'])

    if group != "None" and group != 'All':
        gid = GroupDetail.objects.get(
            GroupName=group, user=request.user).id
        entry = entry.filter(Order__OrderGroup_id=gid)
        order = order.filter(OrderGroup_id=gid)
    if IPOType != "None" and IPOType != 'All':
        entry = entry.filter(Order__OrderCategory=IPOType)
        order = order.filter(OrderCategory=IPOType)

    if IPOName.IPOType == "MAINBOARD":    
        if InvestorType != "None" and InvestorType != 'All':
            entry = entry.filter(Order__InvestorType=InvestorType)
            order = order.filter(InvestorType=InvestorType)
        for member in entry.filter().values_list('Order__OrderGroup__GroupName', 'Order__OrderCategory', 'Order__InvestorType', 'Order__OrderType', 'Order__Rate', 'AllotedQty', 'PreOpenPrice','Amount', 'OrderDetailPANNo__PANNo', 'OrderDetailPANNo__Name'):
            writer.writerow(member)
        for member in order.filter().values_list('OrderGroup__GroupName', 'OrderCategory', 'InvestorType', 'OrderType', 'Rate', 'Quantity','OrderIPOName__PreOpenPrice', 'Amount'):
            writer.writerow(member)
    else:
        for member in entry.filter().values_list('Order__OrderGroup__GroupName', 'Order__OrderCategory', 'Order__OrderType', 'Order__Rate', 'AllotedQty', 'PreOpenPrice', 'Amount', 'OrderDetailPANNo__PANNo', 'OrderDetailPANNo__Name'):
            writer.writerow(member)
        for member in order.filter().values_list('OrderGroup__GroupName', 'OrderCategory', 'OrderType', 'Rate', 'Quantity','OrderIPOName__PreOpenPrice', 'Amount'):
            writer.writerow(member)

    response['Content-Disposition'] = f'attachment; filename="{IPOName}-Billing.csv"'

    return response

#Group Wise Dashboard  billing download PDF fun
def exportGroupwise(request):

    Group = GroupDetail.objects.filter(user=request.user)
    IPO = CurrentIpoName.objects.filter(user=request.user)
    response = HttpResponse(content_type='text/csv')

    grpname = []
    Collectionlist = []
    IPOName = []
    IPOAmount = []
    nlist = []
    Total = 0
    l = []
    for IpoName in IPO:
        entry = Order.objects.filter(
            user=request.user, OrderIPOName=IpoName)
        total = 0
        for i in entry:
            total = total + i.Amount
        Total =Total + total
        if (total!=0):
            IPOAmount.append(total)
            IPOName.append(IpoName)

    lenofipo = len(IPOName)
    for j in range(0, lenofipo):
        l.append(j)
    SumCollection = 0
    for GroupName in Group:
        SumCollection = SumCollection + GroupName.Collection
        grpname.append(GroupName)
        Collectionlist.append(GroupName.Collection)
    lenofgroup = len(grpname)

    for GroupName in Group:
        IPOTotal = []
        for IpoName in IPOName:

            total = 0
            DueAmount = 0
            entry = Order.objects.filter(
                user=request.user, OrderGroup=GroupName, OrderIPOName=IpoName)
            for i in entry:
            
                total = total + i.Amount
            IPOTotal.append(total)
        nlist.append(IPOTotal)
    
    DueAmountSum = float(Total )- float(SumCollection)
    df = pd.DataFrame(nlist, columns=IPOName, index=grpname)
    df['Total'] = df[IPOName].sum(axis=1)
    df['Collection'] = Collectionlist
    df['Due Amount'] = df['Total'] - df['Collection']

    grpdict =dict(zip (IPOName,IPOAmount))
    grpdict.update({'Total': Total ,'Collection' :SumCollection , 'Due Amount':float(DueAmountSum) })
    df.loc['Total'] = grpdict

    Groupwise = BytesIO()
    with pd.ExcelWriter(Groupwise, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Sheet1')

    response['Content-Disposition'] = f'attachment; filename="GroupWiseDashboard.xlsx"'
    Groupwise.seek(0)
    response.write(Groupwise.read())
    return response


def exportBillingFilterpdf(request, IPOid, group=None, IPOType=None, InvestorType=None):
    group = unquote(group)
    IPOType = unquote(IPOType)
    IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)
    userid = request.user

    entry = OrderDetail.objects.filter(
        user=request.user, Order__OrderIPOName=IPOName)
    order = Order.objects.filter(
        user=request.user, OrderIPOName_id=IPOid, OrderCategory="Premium")   
   
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{IPOName}-Billing.PDF"'

    doc = SimpleDocTemplate(response, pagesize=landscape(letter))

    # Create a centered title for your PDF
    styles = getSampleStyleSheet()
    title = f"<u>{IPOName}</u>"
    centered_title = Paragraph(title, styles['Title'])
    centered_title.alignment = 1  # Center alignment

    IPOName = CurrentIpoName.objects.get(id=IPOid, user=userid)
    IpoPrePrice = IPOName.PreOpenPrice
    IpoPrice = IPOName.IPOPrice
    
    order = Order.objects.filter(
        user=userid, OrderIPOName_id=IPOid, OrderCategory="Premium")

    total = 0
    Total1 = order.aggregate(Sum('Amount'))
    Total = Total1['Amount__sum']
    if Total == None:
        Total = 0
    else:
        Total = Total
    totalorder = total + Total
    Total1 = entry.aggregate(Sum('Amount'))
    Total = Total1['Amount__sum']
    if Total == None:
        Total = 0
    total = total + Total
    total = total + totalorder

    head = []   
    head.append(['IPO PRICE',IpoPrice,'PRE OPEN PRICE',IpoPrePrice,'TOTAL',"{:.0f}".format(total)])

    blank = ['']
 
    if group != "None" and group != 'All':
        gid = GroupDetail.objects.get( GroupName=group, user=request.user).id
        entry = entry.filter(Order__OrderGroup_id=gid)
        order = order.filter(OrderGroup_id=gid)
    if IPOType != "None" and IPOType != 'All':
        entry = entry.filter(Order__OrderCategory=IPOType)
        order = order.filter(OrderCategory=IPOType) 
    
    table_data = []

    if IPOName.IPOType == "MAINBOARD":
        table_data.append(['Group', 'Order Category', 'Investor Type', 'Order Type', 'Rate', 'AllotedQty','Pre-Open Price', 'Amount', 'PAN No','Client Name']) 
    else:
        table_data.append(['Group', 'Order Category', 'Order Type', 'Rate', 'AllotedQty','Pre-Open Price', 'Amount Diff.' ,'PAN No','Client Name'])

 
    if IPOName.IPOType == "MAINBOARD":    
        if InvestorType != "None" and InvestorType != 'All':
            entry = entry.filter(Order__InvestorType=InvestorType)
            order = order.filter(InvestorType=InvestorType)   
        for member in entry.filter().values_list('Order__OrderGroup__GroupName', 'Order__OrderCategory', 'Order__InvestorType', 'Order__OrderType', 'Order__Rate','AllotedQty','PreOpenPrice', 'Amount', 'OrderDetailPANNo__PANNo', 'OrderDetailPANNo__Name' ):
            table_data.append(member)
        for member in order.filter().values_list('OrderGroup__GroupName', 'OrderCategory', 'InvestorType', 'OrderType', 'Rate', 'Quantity','OrderIPOName__PreOpenPrice', 'Amount'):
            table_data.append(member)
    else:
        for member in entry.filter().values_list('Order__OrderGroup__GroupName', 'Order__OrderCategory', 'Order__OrderType', 'Order__Rate',  'AllotedQty', 'PreOpenPrice','Amount','OrderDetailPANNo__PANNo', 'OrderDetailPANNo__Name',):
            table_data.append(member) 
        for member in order.filter().values_list('OrderGroup__GroupName', 'OrderCategory', 'OrderType', 'Rate', 'Quantity','OrderIPOName__PreOpenPrice', 'Amount'):
            table_data.append(member)
        
    table_width= 10.5 * inch
   
    table = Table(table_data,colWidths=[table_width / len(table_data[0])] * len(table_data[0]))    
    h_table = Table(head,colWidths=[table_width / len(head[0])] * len(head[0]))
    h_blank = Table(blank)
 
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),  # Header row background color
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  # Header row text color
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Center align all cells
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Header font
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),  # Header padding
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),  # Data row background color        
        ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Table grid
    ])    
    table.setStyle(style)

    h_style = TableStyle([
        ('BACKGROUND', (0,0 ), (-1, 0), colors.bisque),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10), 
        ('GRID', (0, 0), (-1, -1), 1, colors.black), 
        ('TEXTCOLOR', (0, 0), (0, 0), colors.black),
    ])
    h_table.setStyle(h_style)
 
    elements = []
    elements.append(centered_title)  # Add the centered title
    elements.append(Spacer(1, 12))  # Add some space between title and table

    elements.append(h_blank)
    elements.append(table)
    elements.append(h_blank)
    elements.append(h_table)
    doc.build(elements)
    return response

@allowed_users(allowed_roles=['Broker'])
def Backup(request,IPOid ):

    IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)
    response = HttpResponse(content_type='text/csv')

    entry = OrderDetail.objects.filter(
        user=request.user, Order__OrderIPOName=IPOName)
    order1 = Order.objects.filter(
        user=request.user, OrderIPOName_id=IPOid)       
    order = Order.objects.filter(
        user=request.user, OrderIPOName_id=IPOid, OrderCategory="Premium")   
    # Orders download pdf func     

    data1 = []
    if IPOName.IPOType == "MAINBOARD":
        data1Header = ['Group', 'OrderType','Order Category','Investor Type','Qty' ,'Rate','Amount','Order Date','Order Time']
    else:
        data1Header = ['Group', 'OrderType','Order Category','Qty' ,'Rate','Amount','Order Date','Order Time']        
 
    if IPOName.IPOType == "MAINBOARD":    
      
        for member in order1.filter().values_list('OrderGroup__GroupName', 'OrderType', 'OrderCategory','InvestorType','Quantity', 'Rate','Amount','OrderDate', 'OrderTime' ):
            data1.append(member)   
    else:
        for member in order1.filter().values_list('OrderGroup__GroupName', 'OrderType', 'OrderCategory','Quantity', 'Rate','Amount','OrderDate', 'OrderTime' ):
            data1.append(member)    

    # Client wise billing download pdf func 

    data2 = []

    if entry:
        if IPOName.IPOType == "MAINBOARD":
            data2Header = ['Group', 'Order Category', 'Investor Type', 'Order Type', 'Rate', 'AllotedQty','Pre-Open Price', 'Amount', 'PAN No','Client Name']
        else:
            data2Header = ['Group', 'Order Category', 'Order Type', 'Rate', 'AllotedQty','Pre-Open Price', 'Amount Diff.', 'PAN No','Client Name']
    
    else:
        if IPOName.IPOType == "MAINBOARD":
            data2Header = ['Group', 'Order Category', 'Investor Type', 'Order Type', 'Rate', 'AllotedQty','Pre-Open Price', 'Amount']
        else:
            data2Header = ['Group', 'Order Category', 'Order Type', 'Rate', 'AllotedQty','Pre-Open Price', 'Amount Diff.']
        
        
    if IPOName.IPOType == "MAINBOARD":
        for member in entry.filter().values_list('Order__OrderGroup__GroupName', 'Order__OrderCategory', 'Order__InvestorType', 'Order__OrderType', 'Order__Rate','AllotedQty','PreOpenPrice', 'Amount', 'OrderDetailPANNo__PANNo', 'OrderDetailPANNo__Name' ):
            data2.append(member)
        for member in order.filter().values_list('OrderGroup__GroupName', 'OrderCategory', 'InvestorType', 'OrderType', 'Rate', 'Quantity','OrderIPOName__PreOpenPrice', 'Amount'):
            data2.append(member)
    else:
        for member in entry.filter().values_list('Order__OrderGroup__GroupName', 'Order__OrderCategory', 'Order__OrderType', 'Order__Rate',  'AllotedQty','PreOpenPrice' ,'Amount','OrderDetailPANNo__PANNo', 'OrderDetailPANNo__Name'):
            data2.append(member) 
        for member in order.filter().values_list('OrderGroup__GroupName', 'OrderCategory', 'OrderType', 'Rate', 'Quantity','OrderIPOName__PreOpenPrice', 'Amount'):
            data2.append(member)

    df1 = pd.DataFrame(data1,columns=data1Header)
    df2 = pd.DataFrame(data2,columns=data2Header)


    with pd.ExcelWriter(f'{request.user}-{IPOName}-{datetime.now().strftime("%d-%m-%Y- %H-%M")}.xlsx', engine='xlsxwriter') as writer:
        df1.to_excel(writer, sheet_name='Sheet1', index=False)
        df2.to_excel(writer, sheet_name='Sheet2', index=False)

    with open(f'{request.user}-{IPOName}-{datetime.now().strftime("%d-%m-%Y- %H-%M")}.xlsx', 'rb') as excel_file:
        response = HttpResponse(excel_file.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename={IPOName} {datetime.now().strftime("%d-%m-%Y- %H-%M")} .xlsx'
    
    # Delete the Excel file from the server
    file_path = f'{request.user}-{IPOName}-{datetime.now().strftime("%d-%m-%Y- %H-%M")}.xlsx'

    if os.path.exists(file_path):
        os.remove(file_path)
    return response

def AllIpoBackup(request):
    user = request.user
    IPOs = CurrentIpoName.objects.filter(user=user)

    # Specify the common folder path where you want to save the client-specific folders
    common_folder_path = 'path/to/common/folder'

    # Create a common folder if it doesn't exist
    if not os.path.exists(common_folder_path):
        os.makedirs(common_folder_path)

    for IPO in IPOs:
        IPOid = IPO.id
        current_IPO = CurrentIpoName.objects.get(id=IPOid, user=user)
        response = HttpResponse(content_type='text/csv')

        entry = OrderDetail.objects.filter(user=user, Order__OrderIPOName=current_IPO)
        order1 = Order.objects.filter(user=user, OrderIPOName_id=IPOid)
        order = Order.objects.filter(user=user, OrderIPOName_id=IPOid, OrderCategory="Premium")

        data1 = []
        if current_IPO.IPOType == "MAINBOARD":
            data1Header = ['Group', 'OrderType', 'Order Category', 'Investor Type', 'Qty', 'Rate', 'Amount', 'Order Date', 'Order Time']
        else:
            data1Header = ['Group', 'OrderType', 'Order Category', 'Qty', 'Rate', 'Amount', 'Order Date', 'Order Time']
        
        if current_IPO.IPOType == "MAINBOARD":
            for member in order1.filter().values_list('OrderGroup__GroupName', 'OrderType', 'OrderCategory',
                                                      'InvestorType', 'Quantity', 'Rate', 'Amount', 'OrderDate', 'OrderTime'):
                data1.append(member)
        else:
            for member in order1.filter().values_list('OrderGroup__GroupName', 'OrderType', 'OrderCategory', 'Quantity',
                                                      'Rate', 'Amount', 'OrderDate', 'OrderTime'):
                data1.append(member)

        data2 = []

        if entry:
            if current_IPO.IPOType == "MAINBOARD":
                data2Header = ['Group', 'Order Category', 'Investor Type', 'Order Type', 'Rate', 'AllotedQty',
                               'Pre-Open Price', 'Amount', 'PAN No', 'Client Name']
            else:
                data2Header = ['Group', 'Order Category', 'Order Type', 'Rate', 'AllotedQty', 'Pre-Open Price',
                               'Amount Diff.', 'PAN No', 'Client Name']
        else:
            if current_IPO.IPOType == "MAINBOARD":
                data2Header = ['Group', 'Order Category', 'Investor Type', 'Order Type', 'Rate', 'AllotedQty',
                               'Pre-Open Price', 'Amount']
            else:
                data2Header = ['Group', 'Order Category', 'Order Type', 'Rate', 'AllotedQty', 'Pre-Open Price',
                               'Amount Diff.']

        if current_IPO.IPOType == "MAINBOARD":
            for member in entry.filter().values_list('Order__OrderGroup__GroupName', 'Order__OrderCategory',
                                                      'Order__InvestorType', 'Order__OrderType', 'Order__Rate',
                                                      'AllotedQty', 'PreOpenPrice', 'Amount',
                                                      'OrderDetailPANNo__PANNo', 'OrderDetailPANNo__Name'):
                data2.append(member)
            for member in order.filter().values_list('OrderGroup__GroupName', 'OrderCategory', 'InvestorType',
                                                      'OrderType', 'Rate', 'Quantity', 'OrderIPOName__PreOpenPrice',
                                                      'Amount'):
                data2.append(member)
        else:
            for member in entry.filter().values_list('Order__OrderGroup__GroupName', 'Order__OrderCategory',
                                                      'Order__OrderType', 'Order__Rate', 'AllotedQty', 'PreOpenPrice',
                                                      'Amount', 'OrderDetailPANNo__PANNo', 'OrderDetailPANNo__Name'):
                data2.append(member)
            for member in order.filter().values_list('OrderGroup__GroupName', 'OrderCategory', 'OrderType', 'Rate',
                                                      'Quantity', 'OrderIPOName__PreOpenPrice', 'Amount'):
                data2.append(member)

        df1 = pd.DataFrame(data1, columns=data1Header)
        df2 = pd.DataFrame(data2, columns=data2Header)

        # Create a client-specific folder within the common folder
        client_folder_path = os.path.join(common_folder_path, str(user))
        if not os.path.exists(client_folder_path):
            os.makedirs(client_folder_path)

        file_name = f'{user}-{current_IPO}-{datetime.now().strftime("%d-%m-%Y- %H-%M")}.xlsx'
        file_path = os.path.join(client_folder_path, file_name)

        with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
            df1.to_excel(writer, sheet_name='Sheet1', index=False)
            df2.to_excel(writer, sheet_name='Sheet2', index=False)

    # Provide a zip file containing all Excel files
    zip_filename = f'backup_files-{datetime.now().strftime("%d-%m-%Y- %H-%M")}.zip'
    zip_path = os.path.join(common_folder_path, zip_filename)
    with ZipFile(zip_path, 'w') as zipf:
        for root, dirs, files in os.walk(common_folder_path):
            for file in files:
                zipf.write(os.path.join(root, file), arcname=file)

    # Provide the zip file for download
    with open(zip_path, 'rb') as zip_file:
        response = HttpResponse(zip_file.read(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename={zip_filename}'

    # Clean up: remove the common folder and its contents
    shutil.rmtree(common_folder_path)

    return response

def AccountingBackup(request):
    user = request.user
    entries = Accounting.objects.filter(user=user).select_related("group", "ipo")
    response = HttpResponse(content_type='text/csv')
    # --- Group entries by IPO ---
    ipo_dict = {}
    for e in entries:
        ipo_name = e.ipo.IPOName if e.ipo else (f"{e.ipo_name} (Deleted)" if e.ipo_name else "JV")
        group_name = e.group.GroupName if e.group else (f"{e.group_name} (Deleted)" if e.group_name else "")
        local_dt = timezone.localtime(e.date_time)
    
        row = [
            ipo_name,
            group_name,
            e.amount_type.upper(),
            e.amount,
            e.remark,
            local_dt.strftime("%d-%m-%y %H:%M:%S")
        ]

        if ipo_name not in ipo_dict:
            ipo_dict[ipo_name] = []
        ipo_dict[ipo_name].append(row)
    current_time = datetime.now().strftime("%d-%m-%y_%H-%M-%S")
    response['Content-Disposition'] = f'attachment; filename="Accounting-Backup {current_time}.csv"'
    writer = csv.writer(response)
    writer.writerow(["IPO Name", "Group Name", "Amount Type", "Amount", "Remark", "Date Time"])

    for rows in ipo_dict.values():
        for row in rows:
            writer.writerow(row)

    return response

#app buy-sell panding pan download fun
# @allowed_users(allowed_roles=['Broker', 'Customer'])
def export(request, IPOid, OrderType, group=None, IPOType=None, InvestorType=None, OrderDate=None, OrderTime=None, Rate='All'):
    group=unquote(group)
    IPOType=unquote(IPOType)
    response = HttpResponse(content_type='text/csv')
    has_session_access = request.session.get(f'access_auth_{IPOid}', False)
    if not request.user.is_authenticated and not has_session_access:
        return redirect('login') # Block unauthorized people
    try:
        if request.user.groups.all()[0].name == 'Broker':
            IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)
            entry = OrderDetail.objects.filter(
                user=request.user, Order__OrderIPOName_id=IPOid)
            if group != "None" and group != 'All':
                gid = GroupDetail.objects.get(
                    GroupName=group, user=request.user).id
                entry = entry.filter(Order__OrderGroup_id=gid)
        else:
            entry = OrderDetail.objects.filter(
                user=request.user.Broker_id, Order__OrderIPOName_id=IPOid, Order__OrderGroup_id=request.user.Group_id)
            IPOName = CurrentIpoName.objects.get(
                id=IPOid, user=request.user.Broker_id)
            if group != "None" and group != 'All':
                gid = GroupDetail.objects.get(id=request.user.Group_id).id
                entry = entry.filter(Order__OrderGroup_id=gid)
    except:
        user = request.session[f'link_owner_{IPOid}']
        IPOName = CurrentIpoName.objects.get(id=IPOid, user=user)
        entry = OrderDetail.objects.filter(
                user=user, Order__OrderIPOName_id=IPOid)
        if group != "None" and group != 'All':
            gid = GroupDetail.objects.get(
                GroupName=group, user=user).id
            entry = entry.filter(Order__OrderGroup_id=gid)

    if OrderDate != None and OrderDate != 'None' :
        OrderDate = OrderDate[0:4] +'-'+ OrderDate[4:6]+'-'+ OrderDate[6:8]
        entry = entry.filter(Order__OrderDate = OrderDate)        

    if OrderTime != None and OrderTime != 'None' :
        OrderTime = OrderTime[0:2] + ':' + OrderTime[2:4] + ':' + OrderTime[4:6]
        entry = entry.filter(Order__OrderTime = OrderTime)
    
    if OrderType == "BUY":
        entry = entry.filter(Order__OrderType="BUY")
    if OrderType == "SELL":
        entry = entry.filter(Order__OrderType="SELL")
    writer = csv.writer(response)
    writer.writerow(['Group', 'Order Category', 'Investor Type','Rate', 'PAN No',
                    'Client Name', 'Alloted Qty', 'Demat Number', 'Application Number','Order Date', ' Order Time', 'Remark'])

    if IPOType != "None" and IPOType != 'All':
        entry = entry.filter(Order__OrderCategory=IPOType)
    if InvestorType != "None" and InvestorType != 'All':
        entry = entry.filter(Order__InvestorType=InvestorType)
    if Rate != 'None' and Rate != 'All' and is_valid_queryparam(Rate):
        entry = entry.filter(Order__Rate=float(Rate))

    for member in entry.filter(OrderDetailPANNo_id=None).values_list('Order__OrderGroup__GroupName', 'Order__OrderCategory', 'Order__InvestorType', 'Order__Rate', 'OrderDetailPANNo__PANNo', 'OrderDetailPANNo__Name', 'AllotedQty', 'DematNumber', 'ApplicationNumber', 'Order__OrderDate', 'Order__OrderTime', 'Order__remark'):
        List = list(member)
        List[9] = str(List[9].strftime('%d/%m/%Y'))
        List[11] = format_remark(List[11]) or "-"
        if List[7] != "":
            List[7] = "'" + List[7]
        member = tuple(List)
        writer.writerow(member)

    response['Content-Disposition'] = f'attachment; filename="{IPOName}-OrderDetail.csv"'

    return response

@allowed_users(allowed_roles=['Broker', 'Customer'])
def Group_wise_export(request, IPOid, OrderType, IPOType=None, InvestorType=None, OrderDate=None, OrderTime=None,Rate='All'):
    IPOType = unquote(IPOType) if IPOType else 'All'
    InvestorType = unquote(InvestorType) if InvestorType else 'All'

    # Get IPOName
    if request.user.groups.all()[0].name == 'Broker':
        iponame_obj = CurrentIpoName.objects.get(id=IPOid, user=request.user)
        all_groups = GroupDetail.objects.filter(user=request.user,)
    else:
        # Assuming customers only see their assigned group's data
        iponame_obj = CurrentIpoName.objects.get(id=IPOid, user=request.user.Broker_id)
        all_groups = GroupDetail.objects.filter(id=request.user.Group_id)

    # Create a temporary directory to store CSV files
    temp_dir_name = f'ipo_group_exports_{datetime.now().strftime("%Y%m%d%H%M%S")}'
    temp_dir_path = os.path.join('/tmp', temp_dir_name) # Using /tmp for temporary files, consider a more robust path for production
    os.makedirs(temp_dir_path, exist_ok=True)

    csv_files_to_zip = []

    for group in all_groups:
        entry = OrderDetail.objects.filter(
            Order__OrderIPOName_id=IPOid,
            Order__OrderType=OrderType,
            Order__OrderGroup=group
        )

        if request.user.groups.all()[0].name == 'Broker':
            entry = entry.filter(user=request.user)
        else:
            entry = entry.filter(user=request.user.Broker_id)

        # Apply additional filters if provided
        if OrderDate != None and OrderDate != 'None':
            OrderDate = OrderDate[0:4] + '-' + OrderDate[4:6] + '-' + OrderDate[6:8]
            entry = entry.filter(Order__OrderDate=OrderDate)

        if OrderTime != None and OrderTime != 'None':
            OrderTime = OrderTime[0:2] + ':' + OrderTime[2:4] + ':' + OrderTime[4:6]
            entry = entry.filter(Order__OrderTime=OrderTime)
    
        if IPOType != "None" and IPOType != 'All':
            entry = entry.filter(Order__OrderCategory=IPOType)
        if InvestorType != "None" and InvestorType != 'All':
            entry = entry.filter(Order__InvestorType=InvestorType)
        if Rate != 'None' and Rate != 'All' and is_valid_queryparam(Rate):
            entry = entry.filter(Order__Rate=float(Rate))

        if entry.exists():
            # Create a CSV in memory
            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow(['Group', 'Order Category', 'Investor Type', 'Rate', 'PAN No',
                             'Client Name', 'Alloted Qty', 'Demat Number', 'Application Number', 'Order Date', 'Order Time', 'Remark'])

            # Write data rows
            for member in entry.filter(OrderDetailPANNo_id=None).values_list('Order__OrderGroup__GroupName', 'Order__OrderCategory', 'Order__InvestorType', 'Order__Rate', 'OrderDetailPANNo__PANNo', 'OrderDetailPANNo__Name', 'AllotedQty', 'DematNumber', 'ApplicationNumber', 'Order__OrderDate', 'Order__OrderTime', 'Order__remark'):
                List = list(member)
                if List[9]: # Check if OrderDate is not None
                    List[9] = str(List[9].strftime('%d/%m/%Y'))
                if List[7]: # Check if DematNumber is not None/empty
                    List[7] = "'" + str(List[7]) # Ensure it's a string before prepending "'"
                List[11] = format_remark(List[11]) or "-"
                writer.writerow(List)

            # Save the in-memory CSV to a temporary file
            csv_filename = f'{iponame_obj.IPOName}_{group.GroupName}.csv'
            csv_filepath = os.path.join(temp_dir_path, csv_filename)
            with open(csv_filepath, 'w', newline='', encoding='utf-8') as f:
                f.write(output.getvalue())
            csv_files_to_zip.append(csv_filepath)

    # Create a zip file
    zip_filename = f'{iponame_obj.IPOName}_GroupWiseOrders_{datetime.now().strftime("%Y%m%d%H%M")}.zip'
    zip_filepath = os.path.join('/tmp', zip_filename) # Using /tmp for temporary files, adjust as needed

    with ZipFile(zip_filepath, 'w') as zipf:
        for file_path in csv_files_to_zip:
            zipf.write(file_path, arcname=os.path.basename(file_path))

    # Provide the zip file for download
    with open(zip_filepath, 'rb') as zf:
        response = HttpResponse(zf.read(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename={zip_filename}'

    # Clean up: remove the temporary directory and the zip file
    shutil.rmtree(temp_dir_path)
    os.remove(zip_filepath)

    return response

#app buy-sell all pan download fun
# @allowed_users(allowed_roles=['Broker', 'Customer'])
def exportall(request, IPOid, OrderType, group=None, IPOType=None, InvestorType=None, OrderDate=None, OrderTime=None,Rate='All'):
    group = unquote(group)
    IPOType = unquote(IPOType)
    response = HttpResponse(content_type='text/csv')
    has_session_access = request.session.get(f'access_auth_{IPOid}', False)
    if not request.user.is_authenticated and not has_session_access:
        return redirect('login') # Block unauthorized people
    try:
        if request.user.groups.all()[0].name == 'Broker':
            IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)
            entry = OrderDetail.objects.filter(
                user=request.user, Order__OrderIPOName_id=IPOid)
            if group != "None" and group != 'All':
                gid = GroupDetail.objects.get(
                    GroupName=group, user=request.user).id
                entry = entry.filter(Order__OrderGroup_id=gid)
        else:
            entry = OrderDetail.objects.filter(
                user=request.user.Broker_id, Order__OrderIPOName_id=IPOid, Order__OrderGroup_id=request.user.Group_id)
            IPOName = CurrentIpoName.objects.get(
                id=IPOid, user=request.user.Broker_id)
            if group != "None" and group != 'All':
                gid = GroupDetail.objects.get(id=request.user.Group_id).id
                entry = entry.filter(Order__OrderGroup_id=gid)
    except:
        user = request.session[f'link_owner_{IPOid}']
        IPOName = CurrentIpoName.objects.get(id=IPOid, user=user)
        entry = OrderDetail.objects.filter(
                user=user, Order__OrderIPOName_id=IPOid)
        if group != "None" and group != 'All':
            gid = GroupDetail.objects.get(
                GroupName=group, user=user).id
            entry = entry.filter(Order__OrderGroup_id=gid)

    if OrderDate != None and OrderDate != 'None':
        OrderDate = OrderDate[0:4] +'-'+ OrderDate[4:6] + '-' + OrderDate[6:8]
        entry = entry.filter(Order__OrderDate = OrderDate)        

    if OrderTime != None and OrderTime != 'None' :
        OrderTime = OrderTime[0:2] + ':' + OrderTime[2:4] + ':' + OrderTime[4:6]
        entry = entry.filter(Order__OrderTime = OrderTime)

    if OrderType == "BUY":
        entry = entry.filter(Order__OrderType="BUY")
    if OrderType == "SELL":
        entry = entry.filter(Order__OrderType="SELL")

    writer = csv.writer(response)
    writer.writerow(['Group', 'IPO Type', 'Investor Type', 'Rate', 'PAN No',
                    'Client Name', 'AllotedQty', 'Demat Number', 'Application Number', 'Order Date', 'Order Time','Remark'])

    if IPOType != "None" and IPOType != 'All':
        entry = entry.filter(Order__OrderCategory=IPOType)
    if InvestorType != "None" and InvestorType != 'All':   
        entry = entry.filter(Order__InvestorType=InvestorType)
    if Rate != 'None' and Rate != 'All' and is_valid_queryparam(Rate):
        entry = entry.filter(Order__Rate=float(Rate))
    
    entry = entry.order_by('Order__OrderGroup__GroupName', 'Order__Rate')
    for member in entry.filter().values_list('Order__OrderGroup__GroupName', 'Order__OrderCategory', 'Order__InvestorType','Order__Rate', 'OrderDetailPANNo__PANNo', 'OrderDetailPANNo__Name', 'AllotedQty','DematNumber', 'ApplicationNumber', 'Order__OrderDate', 'Order__OrderTime', 'Order__remark'):
        List = list(member)
        List[9] = str(List[9].strftime('%d/%m/%Y'))
        List[11]= format_remark(List[11]) or "-"
        if List[7] != "":
            List[7] = "'" + List[7]
        member = tuple(List)
        writer.writerow(member)
    response['Content-Disposition'] = f'attachment; filename="{IPOName}-OrderDetail-AllRecords.csv"'

    return response

@allowed_users(allowed_roles=['Broker', 'Customer'])
def Group_wise_exportall(request, IPOid, OrderType, IPOType=None, InvestorType=None, OrderDate=None, OrderTime=None,Rate='All'):
    IPOType = unquote(IPOType) if IPOType else 'All'
    InvestorType = unquote(InvestorType) if InvestorType else 'All'

    # Get IPOName
    if request.user.groups.all()[0].name == 'Broker':
        iponame_obj = CurrentIpoName.objects.get(id=IPOid, user=request.user)
        all_groups = GroupDetail.objects.filter(user=request.user,)
    else:
        # Assuming customers only see their assigned group's data
        iponame_obj = CurrentIpoName.objects.get(id=IPOid, user=request.user.Broker_id)
        all_groups = GroupDetail.objects.filter(id=request.user.Group_id)

    # Create a temporary directory to store CSV files
    temp_dir_name = f'ipo_group_exports_{datetime.now().strftime("%Y%m%d%H%M%S")}'
    temp_dir_path = os.path.join('/tmp', temp_dir_name) # Using /tmp for temporary files, consider a more robust path for production
    os.makedirs(temp_dir_path, exist_ok=True)

    csv_files_to_zip = []

    for group in all_groups:
        entry = OrderDetail.objects.filter(
            Order__OrderIPOName_id=IPOid,
            Order__OrderType=OrderType,
            Order__OrderGroup=group
        )

        if request.user.groups.all()[0].name == 'Broker':
            entry = entry.filter(user=request.user)
        else:
            entry = entry.filter(user=request.user.Broker_id)

        # Apply additional filters if provided
        if OrderDate != None and OrderDate != 'None':
            OrderDate = OrderDate[0:4] + '-' + OrderDate[4:6] + '-' + OrderDate[6:8]
            entry = entry.filter(Order__OrderDate=OrderDate)

        if OrderTime != None and OrderTime != 'None':
            OrderTime = OrderTime[0:2] + ':' + OrderTime[2:4] + ':' + OrderTime[4:6]
            entry = entry.filter(Order__OrderTime=OrderTime)
    
        if IPOType != "None" and IPOType != 'All':
            entry = entry.filter(Order__OrderCategory=IPOType)
        if InvestorType != "None" and InvestorType != 'All':
            entry = entry.filter(Order__InvestorType=InvestorType)

        if entry.exists():
            # Create a CSV in memory
            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow(['Group', 'Order Category', 'Investor Type', 'Rate', 'PAN No',
                             'Client Name', 'Alloted Qty', 'Demat Number', 'Application Number', 'Order Date', 'Order Time', 'Remark'])

            # Write data rows
            for member in entry.values_list('Order__OrderGroup__GroupName', 'Order__OrderCategory', 'Order__InvestorType', 'Order__Rate', 'OrderDetailPANNo__PANNo', 'OrderDetailPANNo__Name', 'AllotedQty', 'DematNumber', 'ApplicationNumber', 'Order__OrderDate', 'Order__OrderTime', 'Order__remark'):
                List = list(member)
                if List[9]: # Check if OrderDate is not None
                    List[9] = str(List[9].strftime('%d/%m/%Y'))
                if List[7]: # Check if DematNumber is not None/empty
                    List[7] = "'" + str(List[7]) # Ensure it's a string before prepending "'"
                
                List[11] = format_remark(List[11]) or ''
                writer.writerow(List)

            # Save the in-memory CSV to a temporary file
            csv_filename = f'{iponame_obj.IPOName}_{group.GroupName}.csv'
            csv_filepath = os.path.join(temp_dir_path, csv_filename)
            with open(csv_filepath, 'w', newline='', encoding='utf-8') as f:
                f.write(output.getvalue())
            csv_files_to_zip.append(csv_filepath)

    # Create a zip file
    zip_filename = f'{iponame_obj.IPOName}_GroupWiseOrders_{datetime.now().strftime("%Y%m%d%H%M")}.zip'
    zip_filepath = os.path.join('/tmp', zip_filename) # Using /tmp for temporary files, adjust as needed

    with ZipFile(zip_filepath, 'w') as zipf:
        for file_path in csv_files_to_zip:
            zipf.write(file_path, arcname=os.path.basename(file_path))

    # Provide the zip file for download
    with open(zip_filepath, 'rb') as zf:
        response = HttpResponse(zf.read(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename={zip_filename}'

    # Clean up: remove the temporary directory and the zip file
    shutil.rmtree(temp_dir_path)
    os.remove(zip_filepath)

    return response


# @allowed_users(allowed_roles=['Broker', 'Customer'])
def Error_csv(request):

    try:
        IPOid = request.session.get(f'access_auth_ipo', False)
        has_session_access = request.session.get(f'access_auth_{IPOid}', False)
    except:
        has_session_access = False

    if not request.user.is_authenticated and not has_session_access:
        return redirect('login') # Block unauthorized people

    msg = messages.get_messages(request)
    response = HttpResponse(content_type='text/csv')
    writer = csv.writer(response)

    if request.method == "POST":
        msg = request.POST.get('name', '')
        list1 = msg.split("Row [")

        writer.writerow(['Group', 'Order Category', 'Investor Type', 'Rate', 'PAN No', 'Client Name', 'AllotedQty', 'Demat Number', 'Application Number', 'Order Date', 'Order Time', 'Error'])
    
        for i in list1:
            list2 = ['']
            list3=""

            idx = i.find("]")
            for j in i[idx:]:
                list3 = list3 + j
        
            y = i.replace(list3, "")
            elements = y.split(",")
            elements = [element.strip().strip("'").strip('"') for element in elements]
            if elements != list2:
                writer.writerow(elements)

        response['Content-Disposition'] = f'attachment; filename="Errors_in_Upload-{datetime.now().strftime("%d-%m-%Y- %H-%M-%S")}.csv"'
    
        return response

# @allowed_users(allowed_roles=['Broker', 'Customer'])
# @allowed_users(allowed_roles=['Broker', 'Customer'])
def OrderDetail_upload(request, IPOid, OrderType, GrpName, OrderCategory, InvestorType, OrderDate, OrderTime, Rate='All'):
    has_session_access = request.session.get(f'access_auth_{IPOid}', False)
    if not request.user.is_authenticated and not has_session_access:
        return redirect('login') # Block unauthorized people

    if has_session_access:
        user = request.session[f'link_owner_{IPOid}']
        user_id = CustomUser.objects.get(id=user)
        user_obj = user_id
    else:
        if request.user.groups.all()[0].name == 'Broker':
            user_id = request.user
            user_obj = CustomUser.objects.get(id=request.user.id)
        else:
            user_id = request.user.Broker_id
            user_obj = CustomUser.objects.get(id=request.user.Broker_id)

    start_time = time.time()

    csv_file = request.FILES.get('file')
    if not csv_file or not csv_file.name.endswith('.csv'):
        messages.error(request, 'Please upload a valid CSV file.')
        return redirect(request.META.get('HTTP_REFERER'))

    try:
        data_set = csv_file.read().decode('windows-1252')
    except:
        data_set = csv_file.read().decode('utf-8')

    io_string = io.StringIO(data_set)
    next(io_string)  # Skip header

    reader = csv.reader(io_string, delimiter=',', quotechar='"')
    rows = []  
    for row in reader:
        cleaned_row = [col.strip().strip('"').strip("'") for col in row]
        if any(cleaned_row):  # skip completely blank rows
            rows.append(cleaned_row)

    # Preload groups for faster access
    groups = {g.GroupName: g for g in GroupDetail.objects.filter(user_id=user_id)}

    # PRELOAD CLIENTS: Significant performance optimization (Dictionary Cache)
    # This prevents N+1 queries by fetching all existing clients for this user once.
    clients_dict = {c.PANNo.upper().strip(): c for c in ClientDetail.objects.filter(user_id=user_id)}

    # Load all OrderDetails for matching
    orderdetails_qs = OrderDetail.objects.select_related('Order', 'Order__OrderGroup', 'OrderDetailPANNo').filter(
        user_id=user_id,
        Order__OrderIPOName_id=IPOid,
        Order__OrderType=OrderType
    )

    # Build fast lookup dict for existing non-empty rows to detect duplicates in the database
    existing_details_by_pan = {od.OrderDetailPANNo.PANNo.upper().strip(): od for od in orderdetails_qs if od.OrderDetailPANNo}

    # PRELOAD LOOKUP MAPS: Performance Fix (O(1) lookups instead of O(N) loop)
    # This prevents the 5-minute hang by avoiding 400+ Million comparisons
    precise_orders_map = {}
    flexible_orders_map = {}

    for od in orderdetails_qs:
        if not od.OrderDetailPANNo:
            # Precise Key: HH:MM:SS
            otime = str(od.Order.OrderTime) if od.Order.OrderTime else ""
            p_key = (
                od.Order.OrderGroup.GroupName,
                od.Order.OrderCategory,
                od.Order.InvestorType,
                od.Order.Rate,
                str(od.Order.OrderDate),
                otime
            )
            # Flexible Key: HH:MM
            f_key = p_key[:-1] + (otime[:5],)
        
            precise_orders_map.setdefault(p_key, []).append(od)
            flexible_orders_map.setdefault(f_key, []).append(od)

    used_order_ids = set()

    def pop_order_optimized(p_key):
        """Finds an empty order using precise match, fallback to flexible match (ignoring seconds)"""
        # 1. Try Precise Match (HH:MM:SS)
        for od in precise_orders_map.get(p_key, []):
            if od.id not in used_order_ids:
                used_order_ids.add(od.id)
                return od
    
        # 2. Try Flexible Match (HH:MM) - Restores functionality for approximate CSV times
        f_key = p_key[:-1] + (p_key[-1][:5],)
        for od in flexible_orders_map.get(f_key, []):
            if od.id not in used_order_ids:
                used_order_ids.add(od.id)
                return od
        return None

    issues = []
    updates = []
    processed_pans_this_request = set()

    with transaction.atomic():
        for i, col in enumerate(rows, start=1):
            try:
                if len(col) < 11:
                    continue
            
                group = col[0]
                category = col[1]
                investor = col[2]
                rate = float(col[3])
                pan = col[4].upper().strip()
                name = col[5]
                allot_qty = col[6]
                demat = col[7]
                app_no = col[8]
                date_raw = col[9]
                otime_raw = col[10]

                if not pan or not isValidPAN(pan):
                    messages.error(request, f"Row {i}: Invalid or missing PAN '{pan}'. Skipping.")
                    continue
            
                # Check for duplicate PANs in the SAME CSV upload
                if pan in processed_pans_this_request:
                    messages.error(request, f"Row {i}: Duplicate PAN '{pan}' found in the same CSV upload. Skipping second occurrence.")
                    continue
                processed_pans_this_request.add(pan)

                # Normalize date
                try:
                    if "/" in date_raw:
                        p = date_raw.split("/")
                        date_obj = f"{p[2]}-{p[1].zfill(2)}-{p[0].zfill(2)}"
                    else:
                        p = date_raw.split("-")
                        date_obj = f"{p[0] if len(p[0])==4 else p[2]}-{p[1].zfill(2)}-{p[2] if len(p[0])==4 else p[0].zfill(2)}"
                except:
                    messages.error(request, f"Row {i}: Invalid date format '{date_raw}'. Use DD/MM/YYYY.")
                    continue

                # Time parsing with support for seconds (Required for precision)
                try:
                    parsed_time = None
                    for fmt in ("%H:%M:%S", "%H:%M"):
                        try:
                            parsed_time = datetime.strptime(otime_raw.strip(), fmt).time()
                            break
                        except: continue
                    if not parsed_time:
                        raise ValueError("Invalid time")
                    # Match precision requirements: use full HH:MM:SS
                    time_key = parsed_time.strftime("%H:%M:%S")
                except:
                    messages.error(request, f"Row {i}: Invalid time format '{otime_raw}'. Use HH:MM:SS or HH:MM.")
                    continue

                # Get Group Object for the client creation
                group_obj = groups.get(group)
                if not group_obj:
                    messages.error(request, f"Row {i}: Group '{group}' not found.")
                    continue

                # Use Cache instead of database hit for every row
                client = clients_dict.get(pan)
                if not client:
                    client = ClientDetail.objects.create(
                        user=user_id,
                        PANNo=pan,
                        Name=name,
                        Group=group_obj
                    )
                    clients_dict[pan] = client
                else:
                    # Sync Client Name/Group if changed
                    if client.Name != name or client.Group != group_obj:
                        client.Name = name
                        client.Group = group_obj
                        client.save()

                # Check if this PAN is already allotted in another row for this IPO
                if pan in existing_details_by_pan:
                    od = existing_details_by_pan[pan]
                    # Update existing row instead of failing
                    if request.user.is_authenticated:
                        od.AllotedQty = None if allot_qty == '' else allot_qty
                    od.DematNumber = demat
                    od.ApplicationNumber = app_no
                    updates.append(od)
                    continue

                # Match empty row using the Optimized Hash Map
                key = (group, category, investor, rate, date_obj, time_key)
                od = pop_order_optimized(key)
                if od:
                    od.OrderDetailPANNo = client
                    if request.user.is_authenticated:
                        od.AllotedQty = None if allot_qty == '' else allot_qty
                    od.DematNumber = demat
                    od.ApplicationNumber = app_no
                    updates.append(od)
                else:
                    messages.error(request, f"Row {i}: No corresponding empty order record found for Group={group}, Rate={rate}, Date={date_obj}, Time={time_key}.")

            except Exception as e:
                messages.error(request, f"Row {i} Error: {str(e)}")
                continue
            
        # Bulk update final results
        if updates:
            OrderDetail.objects.bulk_update(
                updates, 
                ['OrderDetailPANNo', 'AllotedQty', 'DematNumber', 'ApplicationNumber'],
                batch_size=2000
            )

    calculate(IPOid, user_id)

    if has_session_access:
        link_id = request.session.get('access')
        return redirect('resolve_shared_link', link_id=link_id, order_type=OrderType)
    else:
        if GrpName == 'None' and OrderCategory == 'None' and InvestorType == 'None':
            return redirect(f"/{IPOid}/OrderDetail/{OrderType}")
        return redirect(f"/{IPOid}/OrderDetail/{OrderType}/{GrpName}/{OrderCategory}/{InvestorType}/{OrderDate}/{OrderTime}/{Rate}")

def Sempale_Order(request,IPOid):
    response = HttpResponse(content_type='text/csv')
    IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)

    writer = csv.writer(response)
    if IPOName.IPOType == "MAINBOARD":
        writer.writerow(['GroupName', 'Ordertype', 'OrderCategory', 'InvestorType', 'Quantity', 'Rate','StrikPrice','OrderDate', 'OrderTime', 'Remark'])
    else:
        writer.writerow(['GroupName', 'Ordertype', 'OrderCategory', 'InvestorType', 'Quantity', 'Rate','StrikPrice','OrderDate', 'OrderTime', 'Remark'])
    
    response['Content-Disposition'] = f'attachment; filename="Order-Sample.csv"'

    return response

def Order_upload(request, IPOid, Groupfilter, Ordercatagoryfilter, InvestorTypefilter):
    csv_file = request.FILES['file']
    if not csv_file.name.endswith('.csv'):
        messages.info(request, 'THIS IS NOT A CSV FILE', extra_tags='error')
    else:
        data_set = csv_file.read().decode('windows-1252')

        io_string = io.StringIO(data_set)
        next(io_string)
        try:
            uid = request.user
            user = request.user
            IPOName = CurrentIpoName.objects.get(id=IPOid, user=user)
            PreOpenPrice = IPOName.PreOpenPrice
        
            for column in csv.reader(io_string, delimiter=',', quotechar="|"):
            
                if len(column) >= 6 :
                    column_mappings = {
                        1: {'BUY': 'BUY', 'SELL': 'SELL'},
                        2: {'KOSTAK': 'Kostak', 'SUBJECT TO': 'Subject To', 'PREMIUM': 'Premium','CALL':'CALL','CALL':'CALL'},
                        3: {'BHNI': 'BHNI', 'PREMIUM': 'PREMIUM', 'RETAIL': 'RETAIL', 'SHNI': 'SHNI','OPTIONS':'OPTIONS'}
                    }

                    # Iterate over the columns and apply the mapping
                    for col_index, mapping in column_mappings.items():
                        column_value = column[col_index].strip().upper()
                        if column_value in mapping:
                            column[col_index] = mapping[column_value]
                    if (    
                        (column[1].strip() in ['BUY', 'SELL']) and
                        (column[2].strip() in ['Kostak', 'Subject To', 'Premium', 'CALL', 'PUT']) and
                        (column[3].strip() in ['BHNI', 'PREMIUM', 'RETAIL', 'SHNI', 'OPTIONS'])
                    ):
            
                        try:
                            GroupName = column[0].strip().upper()
                            gid = GroupDetail.objects.get(GroupName=GroupName, user=user).id
                            O_type= column[1]
                            O_Category = column[2]
                            if IPOName.IPOType == "MAINBOARD":
                                O_InvestorType = column[3].strip()
                                O_Quantity = int(column[4].strip())
                                if O_Quantity <= 0:
                                    raise ValueError("O_Quantity must be a positive value greater than zero.")
                                O_Rate = float(column[5].strip())
                                O_StrikePrice = column[6].strip()
                                if O_Rate <= 0: 
                                    raise ValueError("O_Quantity must be a positive value greater than zero.")
                            else:
                                O_InvestorType = 'RETAIL'
                                O_Quantity = column[4]
                                O_Rate = column[5]
                                O_StrikePrice = column[6].strip()
                            
                            # O_Date = datetime.now().strftime("%Y-%m-%d")
                            # O_Time = datetime.now().strftime("%H:%M:%S")
                        
                            # FLEXIBLE DATE AND TIME PARSING
                            # ========================================
                        
                            # Extract date and time from CSV (columns 7 and 8)
                            if len(column) >= 9:
                                date_raw = column[7].strip() if len(column) > 7 else ""
                                time_raw = column[8].strip() if len(column) > 8 else ""
                            else:
                                date_raw = ""
                                time_raw = ""
                            
                            # Remark Processing
                            remark_json = {}
                            if len(column) >= 10:
                                raw_remark = column[9].strip()
                                valid_tags = ["First Day Bidding", "Subject to + Fix Charges Amount:", "Profit Sharing", "Shareholder Application"]
                                extracted_tags = []
                                clean_text = raw_remark
                                for tag in valid_tags:
                                    if tag in clean_text:
                                        extracted_tags.append(tag)
                                        clean_text = clean_text.replace(tag, "")
                            
                                clean_text = clean_text.strip()
                                # Basic cleanup of punctuation left behind e.g. ", ,"
                                if clean_text.startswith(','):
                                    clean_text = clean_text[1:].strip()
                                if clean_text.endswith(','):
                                    clean_text = clean_text[:-1].strip()
                                
                                if extracted_tags or clean_text:
                                    remark_json = {'tags': extracted_tags, 'text': clean_text}
                        
                            # Default to current date/time
                            O_Date = datetime.now().strftime("%Y-%m-%d")
                            O_Time = datetime.now().strftime("%H:%M:%S")
                            date_time_warnings = []
                        
                            # Try to parse user-provided date
                            if date_raw:
                                try:
                                    parsed_date = None
                                    # Try DD/MM/YYYY format (e.g., 02/10/2025)
                                    if "/" in date_raw:
                                        date_parts = date_raw.split("/")
                                        if len(date_parts) == 3:
                                            O_Date = f"{date_parts[2]}-{date_parts[1].zfill(2)}-{date_parts[0].zfill(2)}"
                                            parsed_date = datetime.strptime(O_Date, "%Y-%m-%d").date()
                                    # Try DD-MM-YYYY or YYYY-MM-DD format
                                    elif "-" in date_raw:
                                        date_parts = date_raw.split("-")
                                        if len(date_parts) == 3:
                                            if len(date_parts[0]) == 4:  # YYYY-MM-DD
                                                O_Date = date_raw
                                            else:  # DD-MM-YYYY
                                                O_Date = f"{date_parts[2]}-{date_parts[1].zfill(2)}-{date_parts[0].zfill(2)}"
                                            parsed_date = datetime.strptime(O_Date, "%Y-%m-%d").date()
                                
                                    # Check if date is in future
                                    if parsed_date and parsed_date > datetime.now().date():
                                        O_Date = datetime.now().strftime("%Y-%m-%d")
                                        date_time_warnings.append("future date detected, using current date")
                                except Exception as e:
                                    O_Date = datetime.now().strftime("%Y-%m-%d")
                                    date_time_warnings.append(f"invalid date format '{date_raw}', using current date")
                        
                            # Try to parse user-provided time (24-hour format HH:MM:SS)
                            if time_raw:
                                try:
                                    time_raw_clean = time_raw.strip()
                                    # Parse 24-hour format HH:MM:SS (e.g., 15:30:21 for 3:30 PM)
                                    time_obj = datetime.strptime(time_raw_clean, "%H:%M:%S")
                                    O_Time = time_obj.strftime("%H:%M:%S")
                                except Exception as e:
                                    O_Time = datetime.now().strftime("%H:%M:%S")
                                    date_time_warnings.append(f"invalid time format '{time_raw}', use HH:MM:SS (24-hour)")
                        
                            # Show consolidated warning if any date/time issues
                            if date_time_warnings:
                                warning_msg = f"Row {column}: " + "; ".join(date_time_warnings)
                                messages.warning(request, warning_msg)
                        
                            if O_type == 'BUY':
                                a = 0
                                if (
                                        O_Category.strip().upper() != 'PREMIUM'
                                        and O_InvestorType.strip().upper() != 'PREMIUM'
                                        and O_InvestorType.strip().upper() != 'CALL'
                                        and O_Category.strip().upper() != 'PUT'
                                        and O_InvestorType.strip().upper() != 'OPTIONS'
                                    ):
                                    if O_Quantity != '' and O_Quantity != "0" and O_Rate != '':
                                        # order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType = O_InvestorType,
                                        #     OrderCategory=O_Category, OrderType=O_type, Quantity=O_Quantity, Rate=O_Rate, OrderDate=O_Date, OrderTime = O_Time)
                                        if O_StrikePrice.strip().upper() == 'PREMIUM':
                                            order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType = O_InvestorType,
                                                OrderCategory=O_Category, OrderType=O_type, Quantity=O_Quantity, Rate=O_Rate, OrderDate=O_Date, OrderTime = O_Time, Method='Premium', remark=remark_json)
                                        else:
                                            order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType = O_InvestorType,
                                                OrderCategory=O_Category, OrderType=O_type, Quantity=O_Quantity, Rate=O_Rate, OrderDate=O_Date, OrderTime = O_Time, remark=remark_json)
                    
                                        O_limit  = CustomUser.objects.get( username = user)
                                        if O_limit.Order_limit is not None :
                                            BUY_Count = OrderDetail.objects.filter(user=user,Order__OrderIPOName_id= IPOid).count()
                                            Sum_Qty = int(BUY_Count) + int(O_Quantity)
                                            Limit  = int(O_limit.Order_limit)

                                            if Sum_Qty >= Limit + 1:
                                                messages.error(request, f"You have reached the limit of {Limit} Order.")
                                                return redirect(f'/{IPOid}/BUY')
                                    
                                        order.save()
                                        a = 1           
                                        Order_Details_update_sync(O_Quantity, uid, order.id, PreOpenPrice)
                                        # for i in range(0, int(O_Quantity)):
                                        #     orderdetail = OrderDetail( user=user, Order_id=order.id , PreOpenPrice = PreOpenPrice)
                                        #     orderdetail.save()
                                elif O_Category.strip().upper() == 'PREMIUM' and O_InvestorType.strip().upper() == 'PREMIUM':
                                    if O_Quantity != '' and O_Quantity != "0" and O_Rate != '':
                                        order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType ='PREMIUM',
                                                        OrderCategory='Premium', OrderType="BUY", Quantity=O_Quantity, Rate=O_Rate, OrderDate=O_Date, OrderTime = O_Time, remark=remark_json)
                                    
                                        O_limit  = CustomUser.objects.get( username = user)
                                        if O_limit.Premium_Order_limit is not None :
                                            Order_type = "Premium"
                                            Pri_QTY = Order.objects.filter(user=user , OrderIPOName_id= IPOid , OrderCategory=Order_type).aggregate(Sum('Quantity'))['Quantity__sum'] 
                                            Sum_Qty = int(Pri_QTY) + int(O_Quantity)
                                            Limit  = int(O_limit.Premium_Order_limit)

                                            if Sum_Qty >= Limit + 1:
                                                messages.error(request, f"You have reached the limit of {Limit} Order.")
                                                return redirect(f'/{IPOid}/BUY')
                                    
                                        order.save()
                                elif O_Category.strip().upper() in ('CALL', 'PUT') and O_InvestorType.strip().upper() == 'OPTIONS':    
                                    if O_Quantity != '' and O_Quantity != "0" and O_Rate != '':
                                        order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType ='OPTIONS',
                                                        OrderCategory= O_Category.strip().upper(), OrderType="BUY", Quantity=O_Quantity, Rate=O_Rate, OrderDate=O_Date, OrderTime = O_Time ,Method = O_StrikePrice, remark=remark_json)
                                    
                                        O_limit  = CustomUser.objects.get( username = user)
                                        if O_limit.Premium_Order_limit is not None :
                                            Order_type = "Premium"
                                            Pri_QTY = Order.objects.filter(user=user , OrderIPOName_id= IPOid , OrderCategory=Order_type).aggregate(Sum('Quantity'))['Quantity__sum'] 
                                            Sum_Qty = int(Pri_QTY) + int(O_Quantity)
                                            Limit  = int(O_limit.Premium_Order_limit)

                                            if Sum_Qty >= Limit + 1:
                                                messages.error(request, f"You have reached the limit of {Limit} Order.")
                                                return redirect(f'/{IPOid}/BUY')
                                    
                                        order.save()     
                            
                                else:
                                    column.append('Error')
                                    messages.error(request, f"Row {column} has error.", extra_tags='error' )
                            else:
                                a = 0
                                # if O_Category != 'Premium' and O_Category != 'premium' and O_Category != 'PREMIUM' and O_InvestorType.strip().upper() != 'PREMIUM':
                                if (
                                    O_Category.strip().upper() != 'PREMIUM'
                                    and O_InvestorType.strip().upper() != 'PREMIUM'
                                    and O_InvestorType.strip().upper() != 'CALL'
                                    and O_Category.strip().upper() != 'PUT'
                                    and O_InvestorType.strip().upper() != 'OPTIONS'
                                ):
                                    if O_Quantity != '' and O_Quantity != "0" and O_Rate != '':
                                        # order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType = O_InvestorType,
                                        #             OrderCategory=O_Category, OrderType="SELL", Quantity=O_Quantity, Rate=O_Rate, OrderDate=O_Date, OrderTime = O_Time)
                                        if O_StrikePrice.strip().upper() == 'PREMIUM':
                                            order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType = O_InvestorType,
                                                        OrderCategory=O_Category, OrderType="SELL", Quantity=O_Quantity, Rate=O_Rate, OrderDate=O_Date, OrderTime = O_Time, Method='Premium', remark=remark_json)
                                        else:
                                            order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType = O_InvestorType,
                                                        OrderCategory=O_Category, OrderType="SELL", Quantity=O_Quantity, Rate=O_Rate, OrderDate=O_Date, OrderTime = O_Time, remark=remark_json)
                                    
                                        O_limit  = CustomUser.objects.get( username = user)
                                
                                        if O_limit.Order_limit is not None :
                                            BUY_Count = OrderDetail.objects.filter(user=user , Order__OrderIPOName_id= IPOid).count()
                                            Sum_Qty = int(BUY_Count) + int(O_Quantity)
                                            Limit  = int(O_limit.Order_limit)

                                            if Sum_Qty >= Limit + 1:
                                                messages.error(request, f"You have reached the limit of {Limit} Order.")
                                                return redirect(f'/{IPOid}/BUY')
                                    
                                        order.save()
                                        a = 1
                                        Order_Details_update_sync(O_Quantity, uid, order.id, PreOpenPrice)
                                        # for i in range(0, int(O_Quantity)):
                                        #     orderdetail = OrderDetail( user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice)
                                        #     orderdetail.save()
                                elif O_Category.strip().upper() == 'PREMIUM' and  O_InvestorType.strip().upper() == 'PREMIUM':
                                    if O_Quantity != '' and O_Quantity != "0" and O_Rate != '':
                                        order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType ='PREMIUM',
                                                        OrderCategory='Premium', OrderType="SELL", Quantity=O_Quantity, Rate=O_Rate, OrderDate=O_Date, OrderTime = O_Time , remark=remark_json)
                                    
                                        PRI_limit  = CustomUser.objects.get( username = user)
                                    
                                        if PRI_limit.Premium_Order_limit is not None :
                                            Order_type = "Premium"
                                            Pri_QTY = Order.objects.filter(user=user , OrderIPOName_id= IPOid , OrderCategory=Order_type).aggregate(Sum('Quantity'))['Quantity__sum']
                                            Sum_Qty = int(Pri_QTY) + int(O_Quantity)
                                            Limit  = int(PRI_limit.Premium_Order_limit)

                                            if Sum_Qty >= Limit + 1:
                                                messages.error(request, f"You have reached the limit of {Limit} Order.")
                                                return redirect(f'/{IPOid}/BUY')
                                    
                                        order.save()
                                    
                                elif O_Category.strip().upper() in ('CALL', 'PUT') and O_InvestorType.strip().upper() == 'OPTIONS':
                                    if O_Quantity != '' and O_Quantity != "0" and O_Rate != '':
                                        order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType ='OPTIONS',
                                                        OrderCategory= O_Category.strip().upper(), OrderType="SELL", Quantity=O_Quantity, Rate=O_Rate, OrderDate=O_Date, OrderTime = O_Time ,Method = O_StrikePrice, remark=remark_json)
                                    
                                        O_limit  = CustomUser.objects.get( username = user)
                                        if O_limit.Premium_Order_limit is not None :
                                            Order_type = "Premium"
                                            Pri_QTY = Order.objects.filter(user=user , OrderIPOName_id= IPOid , OrderCategory=Order_type).aggregate(Sum('Quantity'))['Quantity__sum'] 
                                            Sum_Qty = int(Pri_QTY) + int(O_Quantity)
                                            Limit  = int(O_limit.Premium_Order_limit)

                                            if Sum_Qty >= Limit + 1:
                                                messages.error(request, f"You have reached the limit of {Limit} Order.")
                                                return redirect(f'/{IPOid}/BUY')
                                    
                                        order.save()     
                            
                                else:
                                    column.append('Error')
                                    messages.error(request, f"Row {column} has error.", extra_tags='error' )
                        except:
                            column.append('Error')
                            messages.error(request, f"Row {column} has error.", extra_tags='error' )
                    else:
                        column.append('Error')
                        messages.error(request, f"Row {column} has error.", extra_tags='error')
                else:
                    column.append('Error')
                    messages.error(request, "File Details are invaild.", extra_tags='error')

        except:
            column.append('Error')
            messages.error(request, "File Details are invaild.", extra_tags='error')
        calculate(IPOid, request.user)

    return redirect(f"/{IPOid}/Order/{Groupfilter}/{Ordercatagoryfilter}/{InvestorTypefilter}")

#dashboard form fun
@ allowed_users(allowed_roles=['Broker'])
def dashboardform(request, IPOid, value):

    IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)

    if IPOName.IPOType == "SME":
        if request.method == "POST":
            ExpecetdRetailApplication = request.POST.get(
                'ExpecetdRetailApplication', '')
            ProfitMargin = request.POST.get('ProfitMargin', '')
            Premium = request.POST.get('Premium', '')
            IPO = CurrentIpoName.objects.get(id=IPOid, user=request.user)
            o_IPO=OrderDetail.objects.filter(
                user=request.user, Order__OrderIPOName_id=IPOid)
            if ExpecetdRetailApplication != '':
                IPO.ExpecetdRetailApplication = ExpecetdRetailApplication
            if ProfitMargin != '':
                IPO.ProfitMargin = ProfitMargin
            if Premium != '':
                if value == 'A' or value == 'B':
                    IPO.Premium = Premium
                if value == 'C':
                    IPO.PreOpenPrice = Premium
                    o_IPO.update(PreOpenPrice = Premium) 
            IPO.save()
            if value == 'A':
                return redirect(f"/{IPOid}/Dashboard/A")
            if value == 'B':
                return redirect(f"/{IPOid}/Dashboard/B")
            if value == 'C':
                calculate(IPOid, request.user)
                return redirect(f"/{IPOid}/Dashboard/C")
        return redirect(f"/{IPOid}/Dashboard/A")

    else:
        if request.method == "POST":
            IPO = CurrentIpoName.objects.get(id=IPOid, user=request.user)
            o_IPO=OrderDetail.objects.filter(
                user=request.user, Order__OrderIPOName_id=IPOid)

            if value == "A":
                ExpecetdRetailApplication = request.POST.get(
                    'ExpecetdRetailApplication', '')
                ExpecetdSHNIApplication = request.POST.get(
                    'ExpecetdSHNIApplication', '')
                ExpecetdBHNIApplication = request.POST.get(
                    'ExpecetdBHNIApplication', '')

                if ExpecetdRetailApplication != '':
                    IPO.ExpecetdRetailApplication = ExpecetdRetailApplication
            
                if ExpecetdSHNIApplication != '':
                    IPO.ExpecetdSHNIApplication = ExpecetdSHNIApplication
                else:
                    IPO.ExpecetdSHNIApplication = None
            
                if ExpecetdBHNIApplication != '':
                    IPO.ExpecetdBHNIApplication = ExpecetdBHNIApplication
                else:
                    IPO.ExpecetdBHNIApplication = None 
            
            ProfitMargin = request.POST.get('ProfitMargin', '')
        
            Premium = request.POST.get('Premium', '')

            if ProfitMargin != '':
                IPO.ProfitMargin = ProfitMargin
            if Premium != '':
                if value == 'A' or value == 'B':
                    IPO.Premium = Premium
                if value == 'C':
                    IPO.PreOpenPrice = Premium 
                    o_IPO.update(PreOpenPrice = Premium )
            IPO.save()
            if value == 'A':
                return redirect(f"/{IPOid}/Dashboard/A")
            if value == 'B':
                return redirect(f"/{IPOid}/Dashboard/B")
            if value == 'C':
                calculate(IPOid, request.user)
                return redirect(f"/{IPOid}/Dashboard/C")
        return redirect(f"/{IPOid}/Dashboard/A")

#dashboard fun
@ allowed_users(allowed_roles=['Broker'])
def dashboard(request, IPOid, value):

    IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)

    if IPOName.IPOType == "SME":

        if value == 'B':
            ActualallottedQtyBuy = OrderDetail.objects.filter(
                user=request.user, Order__OrderIPOName_id=IPOid,Order__OrderType="BUY").aggregate(Sum('AllotedQty'))
            ActualallottedQtyBuy = ActualallottedQtyBuy['AllotedQty__sum']

            if ActualallottedQtyBuy == None:
                ActualallottedQtyBuy = 0
        
            ActualallottedQtySell = OrderDetail.objects.filter(
                user=request.user, Order__OrderIPOName_id=IPOid,Order__OrderType="SELL").aggregate(Sum('AllotedQty'))
            ActualallottedQtySell = ActualallottedQtySell['AllotedQty__sum']

            if ActualallottedQtySell == None:
                ActualallottedQtySell = 0
        
            ActualallottedQty = ActualallottedQtyBuy - ActualallottedQtySell
        
            IPO = CurrentIpoName.objects.get(id=IPOid, user=request.user)
            try:
                IPOPremium = float(IPO.Premium)
                if IPOPremium == None:
                    IPOPremium = 0
            except:
                IPOPremium = 0
            if IPO.ProfitMargin == None:
                IPO.ProfitMargin = 15
            IPO.save()
            try:
                LotValue = float(IPO.IPOPrice)*float(IPO.LotSizeRetail)
                RetailSize = ((float(IPO.TotalIPOSzie))
                            * float(IPO.RetailPercentage))/100
                ApplicationFor1Time = (float(RetailSize)*10000000)/LotValue
            except:
                LotValue = 0
                RetailSize = 0
                ApplicationFor1Time = 0
            try:
                ProfitMargin = float(IPO.ProfitMargin)
            except:
                ProfitMargin = None
            try:
                ExpecetdRetailApplication = int(IPO.ExpecetdRetailApplication)
            except:
                ExpecetdRetailApplication = None
            try:
                NumberOfTimeIPO = ExpecetdRetailApplication/ApplicationFor1Time
            except:
                NumberOfTimeIPO = 0
            try:
                AvgShare = float(IPO.LotSizeRetail)/NumberOfTimeIPO
            except:
                AvgShare = 0
            if AvgShare > IPO.LotSizeRetail:
                AvgShare = IPO.LotSizeRetail
            try:
                BaseKostakRate = float(IPOPremium) * AvgShare
            except:
                BaseKostakRate = 0
            try:
                kostakRateForCustomer = BaseKostakRate - \
                    ((BaseKostakRate*float(IPO.ProfitMargin))/100)
            except:
                kostakRateForCustomer = 0
            try:
                BaseSubjectToRate = float(IPOPremium) * float(IPO.LotSizeRetail)
            except:
                BaseSubjectToRate = 0
            try:
                SubjectToRateForCustomer = BaseSubjectToRate - \
                    ((BaseSubjectToRate*float(IPO.ProfitMargin))/100)
            except:
                SubjectToRateForCustomer = 0

            # ShareSellAgainestKostak = AvgShare * noofkostakapplication
            order = Order.objects.filter(
                user=request.user, OrderIPOName_id=IPOid)
            Kostakentry = order.filter(OrderCategory="Kostak")
            NOBUYKostak = Kostakentry.filter(OrderType="BUY")
            NOBUYKostak11 = NOBUYKostak.aggregate(Sum('Quantity'))
            NOBUYKostak1 = NOBUYKostak11['Quantity__sum']
            if NOBUYKostak1 == None:
                CountofBUYKostak = 0
            else:
                CountofBUYKostak = NOBUYKostak1

            Kostakentry = order.filter(OrderCategory="Kostak")
            NOSELLKostak = Kostakentry.filter(OrderType="SELL")
            NOSELLKostak11 = NOSELLKostak.aggregate(Sum('Quantity'))
            NOSELLKostak1 = NOSELLKostak11['Quantity__sum']
            if NOSELLKostak1 == None:
                CountofSELLKostak = 0
            else:
                CountofSELLKostak = NOSELLKostak1

            try:
                CountOfKostak = CountofBUYKostak - CountofSELLKostak
            except:
                CountOfKostak = 0

            Kostakentry = order.filter(OrderCategory="Kostak")
            AmountBUYKostak = Kostakentry.filter(OrderType="BUY")
            AmountBUYKostak11 = AmountBUYKostak.aggregate(Sum('Amount'))
            AmountBUYKostak1 = AmountBUYKostak11['Amount__sum']
            if AmountBUYKostak1 == None:
                AmountofBUYKostak = 0
            else:
                AmountofBUYKostak = AmountBUYKostak1

            Kostakentry = order.filter(OrderCategory="Kostak")
            AmountSELLKostak = Kostakentry.filter(OrderType="SELL")
            AmountSELLKostak11 = AmountSELLKostak.aggregate(Sum('Amount'))
            AmountSELLKostak1 = AmountSELLKostak11['Amount__sum']
            if AmountSELLKostak1 == None:
                AmountofSELLKostak = 0
            else:
                AmountofSELLKostak = AmountSELLKostak1
            try:
                TotalKostakValue = AmountofBUYKostak + AmountofSELLKostak
            except:
                TotalKostakValue = 0
            try:
                KostakAvg = float(TotalKostakValue) / float(CountOfKostak)
            except:
                KostakAvg = 0

            SubjectToentry = order.filter(OrderCategory="Subject To")
            NOBUYSubjectTo = SubjectToentry.filter(OrderType="BUY")
            NOBUYSubjectTo11 = NOBUYSubjectTo.aggregate(Sum('Quantity'))
            NOBUYSubjectTo1 = NOBUYSubjectTo11['Quantity__sum']
            if NOBUYSubjectTo1 == None:
                CountofBUYSubjectTo = 0
            else:
                CountofBUYSubjectTo = NOBUYSubjectTo1

            SubjectToentry = order.filter(OrderCategory="Subject To")
            NOSELLSubjectTo = SubjectToentry.filter(OrderType="SELL")
            NOSELLSubjectTo11 = NOSELLSubjectTo.aggregate(Sum('Quantity'))
            NOSELLSubjectTo1 = NOSELLSubjectTo11['Quantity__sum']
            if NOSELLSubjectTo1 == None:
                CountofSELLSubjectTo = 0
            else:
                CountofSELLSubjectTo = NOSELLSubjectTo1

            try:
                CountOfSubjectTo = CountofBUYSubjectTo - CountofSELLSubjectTo
            except:
                CountOfSubjectTo = 0

            try:
                TotalApplication = CountOfKostak + CountOfSubjectTo
            except:
                TotalApplication = 0
            try:
                ShareTOBeSell = AvgShare * TotalApplication
            except:
                ShareTOBeSell = 0

            SubjectToentry = order.filter(OrderCategory="Subject To")
            AmountBUYSubjectTo = SubjectToentry.filter(OrderType="BUY")
            AmountBUYSubjectTo11 = AmountBUYSubjectTo.aggregate(Sum('Amount'))
            AmountBUYSubjectTo1 = AmountBUYSubjectTo11['Amount__sum']
            if AmountBUYSubjectTo1 == None:
                AmountofBUYSubjectTo = 0
            else:
                AmountofBUYSubjectTo = AmountBUYSubjectTo1

            SubjectToentry = order.filter(OrderCategory="Subject To")
            AmountSELLSubjectTo = SubjectToentry.filter(OrderType="SELL")
            AmountSELLSubjectTo11 = AmountSELLSubjectTo.aggregate(Sum('Amount'))
            AmountSELLSubjectTo1 = AmountSELLSubjectTo11['Amount__sum']
            if AmountSELLSubjectTo1 == None:
                AmountofSELLSubjectTo = 0
            else:
                AmountofSELLSubjectTo = AmountSELLSubjectTo1

            try:
                TotalSubjectToValue = AmountofBUYSubjectTo + AmountofSELLSubjectTo
            except:
                TotalSubjectToValue = 0
            try:

                SubjectToAvg = float(TotalSubjectToValue) / float(CountOfSubjectTo)
            except:
                SubjectToAvg = 0
            TotalCount = CountOfSubjectTo + CountOfKostak

            KostakShareQty = ActualallottedQty

            Premiumentry = order.filter(OrderCategory="Premium")
            QTYBUYPremium = Premiumentry.filter(OrderType="BUY")
            QTYBUYPremium11 = QTYBUYPremium.aggregate(Sum('Quantity'))
            QTYBUYPremium1 = QTYBUYPremium11['Quantity__sum']
            if QTYBUYPremium1 == None:
                TotalBuyPremiumShareQty = 0
            else:
                TotalBuyPremiumShareQty = QTYBUYPremium1

            Premiumentry = order.filter(OrderCategory="Premium")
            QTYSELLPremium = Premiumentry.filter(OrderType="SELL")
            QTYSELLPremium11 = QTYSELLPremium.aggregate(Sum('Quantity'))
            QTYSELLPremium1 = QTYSELLPremium11['Quantity__sum']
            if QTYSELLPremium1 == None:
                TotalSellPremiumShareQty = 0
            else:
                TotalSellPremiumShareQty = QTYSELLPremium1
            try:
                n1 = (KostakAvg/AvgShare)/2
                n2 = (SubjectToAvg/float(IPO.LotSizeRetail))/2
                KostakShareAvg = n1 + n2
            except:
                KostakShareAvg = 0

            try:
                CountOfPremium = TotalBuyPremiumShareQty - TotalSellPremiumShareQty
            except:
                CountOfPremium = 0

            Premiumentry = order.filter(OrderCategory="Premium")
            AmountBUYPremium = Premiumentry.filter(OrderType="BUY")
            AmountBUYPremium11 = AmountBUYPremium.aggregate(Sum('Amount'))
            AmountBUYPremium1 = AmountBUYPremium11['Amount__sum']
            if AmountBUYPremium1 == None:
                TotalBuyPremiumShareAmount = 0
            else:
                TotalBuyPremiumShareAmount = AmountBUYPremium1

            Premiumentry = order.filter(OrderCategory="Premium")
            AmountSELLPremium = Premiumentry.filter(OrderType="SELL")
            AmountSELLPremium11 = AmountSELLPremium.aggregate(Sum('Amount'))
            AmountSELLPremium1 = AmountSELLPremium11['Amount__sum']
            if AmountSELLPremium1 == None:
                TotalSellPremiumShareAmount = 0
            else:
                TotalSellPremiumShareAmount = AmountSELLPremium1
            try:
                BuyPremiumShareAvg = float(
                    TotalBuyPremiumShareAmount) / float(TotalBuyPremiumShareQty)
            except:
                BuyPremiumShareAvg = 0
            try:
                SellPremiumShareAvg = float(
                    TotalSellPremiumShareAmount) / float(TotalSellPremiumShareQty)
            except:
                SellPremiumShareAvg = 0
            try:
                DiffereneQty = (TotalBuyPremiumShareQty+KostakShareQty) - \
                    float(TotalSellPremiumShareQty)
            except:
                DiffereneQty = 0
            try:
                ProfitOrLoss = (SellPremiumShareAvg*TotalSellPremiumShareQty)-((KostakShareQty*KostakShareAvg)+(
                    TotalBuyPremiumShareQty*BuyPremiumShareAvg))+DiffereneQty*float(IPOPremium)
            except:
                ProfitOrLoss = 0
            return render(request, 'Bdashboard_sme.html', {'ActualallottedQty': "{:.2f}".format(ActualallottedQty) ,'ActualallottedQtyBuy': "{:.2f}".format(ActualallottedQtyBuy), 'ActualallottedQtySell': "{:.2f}".format(ActualallottedQtySell), 'CountofBUYKostak': "{:.2f}".format(CountofBUYKostak), 'CountofSELLKostak': "{:.2f}".format(CountofSELLKostak), 'CountOfKostak': "{:.2f}".format(CountOfKostak), 'KostakAvg': "{:.2f}".format(KostakAvg), 'CountofBUYSubjectTo': "{:.2f}".format(CountofBUYSubjectTo), 'CountofSELLSubjectTo': "{:.2f}".format(CountofSELLSubjectTo),'CountOfSubjectTo': "{:.2f}".format(CountOfSubjectTo), 'SubjectToAvg': "{:.2f}".format(SubjectToAvg), 'KostakShareQty': "{:.2f}".format(KostakShareQty), 'TotalBuyPremiumShareQty': "{:.2f}".format(TotalBuyPremiumShareQty), 'TotalSellPremiumShareQty': "{:.2f}".format(TotalSellPremiumShareQty), 'CountOfPremium': "{:.2f}".format(CountOfPremium), 'IPOName': IPO, 'IPOid': IPOid, 'BaseSubjectToRate': "{:.2f}".format(BaseSubjectToRate), 'SubjectToRateForCustomer': "{:.2f}".format(SubjectToRateForCustomer), 'ProfitMargin': ProfitMargin, 'Premium':IPOPremium, 'KostakShareAvg': "{:.2f}".format(KostakShareAvg), 'BuyPremiumShareAvg': "{:.2f}".format(BuyPremiumShareAvg), 'SellPremiumShareAvg': "{:.2f}".format(SellPremiumShareAvg), 'DiffereneQty': "{:.2f}".format(DiffereneQty), 'ProfitOrLoss': "{:.0f}".format(ProfitOrLoss)})
        if value == 'C':
        
            products = Order.objects.filter(user=request.user, OrderIPOName_id=IPOid)
        
            ActualallottedQtyBuy = OrderDetail.objects.filter(
                user=request.user, Order__OrderIPOName_id=IPOid,Order__OrderType="BUY").aggregate(Sum('AllotedQty'))
            ActualallottedQtyBuy = ActualallottedQtyBuy['AllotedQty__sum']

            if ActualallottedQtyBuy == None:
                ActualallottedQtyBuy = 0
        
            ActualallottedQtySell = OrderDetail.objects.filter(
                user=request.user, Order__OrderIPOName_id=IPOid,Order__OrderType="SELL").aggregate(Sum('AllotedQty'))
            ActualallottedQtySell = ActualallottedQtySell['AllotedQty__sum']

            if ActualallottedQtySell == None:
                ActualallottedQtySell = 0
        
            ActualallottedQty = ActualallottedQtyBuy - ActualallottedQtySell
        
            IPO = CurrentIpoName.objects.get(id=IPOid, user=request.user)
            try:
                IPOPremium = float(IPO.Premium)
            except:
                IPOPremium = 0
            if IPO.ProfitMargin == None:
                IPO.ProfitMargin = 15
            if IPO.ExpecetdRetailApplication == None:
                IPO.ExpecetdRetailApplication = 2500000
            IPO.save()
            try:
                LotValue = float(IPO.IPOPrice)*float(IPO.LotSizeRetail)
                RetailSize = ((float(IPO.TotalIPOSzie))
                            * float(IPO.RetailPercentage))/100
                ApplicationFor1Time = (float(RetailSize)*10000000)/LotValue
            except:
                LotValue = 0
                RetailSize = 0
                ApplicationFor1Time = 0
            try:
                ProfitMargin = float(IPO.ProfitMargin)
            except:
                ProfitMargin = None
            try:
                ExpecetdRetailApplication = int(IPO.ExpecetdRetailApplication)
            except:
                ExpecetdRetailApplication = None
            try:
                NumberOfTimeIPO = ExpecetdRetailApplication/ApplicationFor1Time
            except:
                NumberOfTimeIPO = 0
            try:
                AvgShare = float(IPO.LotSizeRetail)/NumberOfTimeIPO
            except:
                AvgShare = 0
            if AvgShare > IPO.LotSizeRetail:
                AvgShare = IPO.LotSizeRetail
            try:
                BaseKostakRate = float(IPOPremium) * AvgShare
            except:
                BaseKostakRate = 0
            try:
                kostakRateForCustomer = BaseKostakRate - \
                    ((BaseKostakRate*float(IPO.ProfitMargin))/100)
            except:
                kostakRateForCustomer = 0
            try:
                BaseSubjectToRate = float(IPOPremium) * float(IPO.LotSizeRetail)
            except:
                BaseSubjectToRate = 0
            try:
                SubjectToRateForCustomer = BaseSubjectToRate - \
                    ((BaseSubjectToRate*float(IPO.ProfitMargin))/100)
            except:
                SubjectToRateForCustomer = 0

            order = Order.objects.filter(
                user=request.user, OrderIPOName_id=IPOid)
            Kostakentry = order.filter(OrderCategory="Kostak")
            NOBUYKostak = Kostakentry.filter(OrderType="BUY")
            NOBUYKostak11 = NOBUYKostak.aggregate(Sum('Quantity'))
            NOBUYKostak1 = NOBUYKostak11['Quantity__sum']
            if NOBUYKostak1 == None:
                CountofBUYKostak = 0
            else:
                CountofBUYKostak = NOBUYKostak1

            Kostakentry = order.filter(OrderCategory="Kostak")
            NOSELLKostak = Kostakentry.filter(OrderType="SELL")
            NOSELLKostak11 = NOSELLKostak.aggregate(Sum('Quantity'))
            NOSELLKostak1 = NOSELLKostak11['Quantity__sum']
            if NOSELLKostak1 == None:
                CountofSELLKostak = 0
            else:
                CountofSELLKostak = NOSELLKostak1

            try:
                CountOfKostak = CountofBUYKostak - CountofSELLKostak
            except:
                CountOfKostak = 0

            Kostakentry = order.filter(OrderCategory="Kostak")
            AmountBUYKostak = Kostakentry.filter(OrderType="BUY")
            AmountBUYKostak11 = AmountBUYKostak.aggregate(Sum('Amount'))
            AmountBUYKostak1 = AmountBUYKostak11['Amount__sum']
            if AmountBUYKostak1 == None:
                AmountofBUYKostak = 0
            else:
                AmountofBUYKostak = AmountBUYKostak1

            Kostakentry = order.filter(OrderCategory="Kostak")
            AmountSELLKostak = Kostakentry.filter(OrderType="SELL")
            AmountSELLKostak11 = AmountSELLKostak.aggregate(Sum('Amount'))
            AmountSELLKostak1 = AmountSELLKostak11['Amount__sum']
            if AmountSELLKostak1 == None:
                AmountofSELLKostak = 0
            else:
                AmountofSELLKostak = AmountSELLKostak1
            try:
                TotalKostakValue = AmountofBUYKostak + AmountofSELLKostak
            except:
                TotalKostakValue = 0
            try:
                KostakAvg = float(TotalKostakValue) / float(CountOfKostak)
            except:
                KostakAvg = 0

            SubjectToentry = order.filter(OrderCategory="Subject To")
            NOBUYSubjectTo = SubjectToentry.filter(OrderType="BUY")
            NOBUYSubjectTo11 = NOBUYSubjectTo.aggregate(Sum('Quantity'))
            NOBUYSubjectTo1 = NOBUYSubjectTo11['Quantity__sum']
            if NOBUYSubjectTo1 == None:
                CountofBUYSubjectTo = 0
            else:
                CountofBUYSubjectTo = NOBUYSubjectTo1

            SubjectToentry = order.filter(OrderCategory="Subject To")
            NOSELLSubjectTo = SubjectToentry.filter(OrderType="SELL")
            NOSELLSubjectTo11 = NOSELLSubjectTo.aggregate(Sum('Quantity'))
            NOSELLSubjectTo1 = NOSELLSubjectTo11['Quantity__sum']
            if NOSELLSubjectTo1 == None:
                CountofSELLSubjectTo = 0
            else:
                CountofSELLSubjectTo = NOSELLSubjectTo1

            try:
                CountOfSubjectTo = CountofBUYSubjectTo - CountofSELLSubjectTo
            except:
                CountOfSubjectTo = 0

            try:
                TotalApplication = CountOfKostak + CountOfSubjectTo
            except:
                TotalApplication = 0
            try:
                ShareTOBeSell = AvgShare * TotalApplication
            except:
                ShareTOBeSell = 0

            SubjectToentry = order.filter(OrderCategory="Subject To")
            AmountBUYSubjectTo = SubjectToentry.filter(OrderType="BUY")
            AmountBUYSubjectTo11 = AmountBUYSubjectTo.aggregate(Sum('Amount'))
            AmountBUYSubjectTo1 = AmountBUYSubjectTo11['Amount__sum']
            if AmountBUYSubjectTo1 == None:
                AmountofBUYSubjectTo = 0
            else:
                AmountofBUYSubjectTo = AmountBUYSubjectTo1

            SubjectToentry = order.filter(OrderCategory="Subject To")
            AmountSELLSubjectTo = SubjectToentry.filter(OrderType="SELL")
            AmountSELLSubjectTo11 = AmountSELLSubjectTo.aggregate(Sum('Amount'))
            AmountSELLSubjectTo1 = AmountSELLSubjectTo11['Amount__sum']
            if AmountSELLSubjectTo1 == None:
                AmountofSELLSubjectTo = 0
            else:
                AmountofSELLSubjectTo = AmountSELLSubjectTo1

            try:
                TotalSubjectToValue = AmountofBUYSubjectTo + AmountofSELLSubjectTo
            except:
                TotalSubjectToValue = 0
            try:

                SubjectToAvg = float(TotalSubjectToValue) / float(CountOfSubjectTo)
            except:
                SubjectToAvg = 0
            TotalCount = CountOfSubjectTo + CountOfKostak

            KostakShareQty = ActualallottedQty

            Premiumentry = order.filter(OrderCategory="Premium")
            QTYBUYPremium = Premiumentry.filter(OrderType="BUY")
            QTYBUYPremium11 = QTYBUYPremium.aggregate(Sum('Quantity'))
            QTYBUYPremium1 = QTYBUYPremium11['Quantity__sum']
            if QTYBUYPremium1 == None:
                TotalBuyPremiumShareQty = 0
            else:
                TotalBuyPremiumShareQty = QTYBUYPremium1

            Premiumentry = order.filter(OrderCategory="Premium")
            QTYSELLPremium = Premiumentry.filter(OrderType="SELL")
            QTYSELLPremium11 = QTYSELLPremium.aggregate(Sum('Quantity'))
            QTYSELLPremium1 = QTYSELLPremium11['Quantity__sum']
            if QTYSELLPremium1 == None:
                TotalSellPremiumShareQty = 0
            else:
                TotalSellPremiumShareQty = QTYSELLPremium1
            try:
                n1 = (KostakAvg/AvgShare)/2
                n2 = (SubjectToAvg/float(IPO.LotSizeRetail))/2
                KostakShareAvg = n1 + n2
            except:
                KostakShareAvg = 0
            try:
                CountOfPremium = TotalBuyPremiumShareQty - TotalSellPremiumShareQty
            except:
                CountOfPremium = 0

            Premiumentry = order.filter(OrderCategory="Premium")
            AmountBUYPremium = Premiumentry.filter(OrderType="BUY")
            AmountBUYPremium11 = AmountBUYPremium.aggregate(Sum('Amount'))
            AmountBUYPremium1 = AmountBUYPremium11['Amount__sum']
            if AmountBUYPremium1 == None:
                TotalBuyPremiumShareAmount = 0
            else:
                TotalBuyPremiumShareAmount = AmountBUYPremium1

            Premiumentry = order.filter(OrderCategory="Premium")
            AmountSELLPremium = Premiumentry.filter(OrderType="SELL")
            AmountSELLPremium11 = AmountSELLPremium.aggregate(Sum('Amount'))
            AmountSELLPremium1 = AmountSELLPremium11['Amount__sum']
            if AmountSELLPremium1 == None:
                TotalSellPremiumShareAmount = 0
            else:
                TotalSellPremiumShareAmount = AmountSELLPremium1
            try:
                BuyPremiumShareAvg = float(
                    TotalBuyPremiumShareAmount) / float(TotalBuyPremiumShareQty)
            except:
                BuyPremiumShareAvg = 0
            try:
                SellPremiumShareAvg = float(
                    TotalSellPremiumShareAmount) / float(TotalSellPremiumShareQty)
            except:
                SellPremiumShareAvg = 0
            try:
                DiffereneQty = (TotalBuyPremiumShareQty+KostakShareQty) - \
                    float(TotalSellPremiumShareQty)
            except:
                DiffereneQty = 0
            try:
                Amountsum= products.aggregate(Sum('Amount'))['Amount__sum']
                ProfitOrLoss = float(Amountsum)
            except:
                ProfitOrLoss = 0
            return render(request, 'Cdashboard_sme.html', {'ActualallottedQty': "{:.2f}".format(ActualallottedQty), 'ActualallottedQtyBuy': "{:.2f}".format(ActualallottedQtyBuy), 'ActualallottedQtySell': "{:.2f}".format(ActualallottedQtySell),  'CountofBUYKostak': "{:.2f}".format(CountofBUYKostak), 'CountofSELLKostak': "{:.2f}".format(CountofSELLKostak),'CountOfKostak': "{:.2f}".format(CountOfKostak), 'KostakAvg': "{:.2f}".format(KostakAvg), 'CountofBUYSubjectTo': "{:.2f}".format(CountofBUYSubjectTo), 'CountofSELLSubjectTo': "{:.2f}".format(CountofSELLSubjectTo),'CountOfSubjectTo': "{:.2f}".format(CountOfSubjectTo), 'SubjectToAvg': "{:.2f}".format(SubjectToAvg), 'KostakShareQty': "{:.2f}".format(KostakShareQty), 'TotalBuyPremiumShareQty': "{:.2f}".format(TotalBuyPremiumShareQty), 'TotalSellPremiumShareQty': "{:.2f}".format(TotalSellPremiumShareQty), 'CountOfPremium': "{:.2f}".format(CountOfPremium), 'IPOName': IPO, 'IPOid': IPOid, 'Premium': IPO.Premium, 'KostakShareAvg': "{:.2f}".format(KostakShareAvg), 'BuyPremiumShareAvg': "{:.2f}".format(BuyPremiumShareAvg), 'SellPremiumShareAvg': "{:.2f}".format(SellPremiumShareAvg), 'DiffereneQty': "{:.2f}".format(DiffereneQty), 'ProfitOrLoss': "{:.0f}".format(ProfitOrLoss)})

        IPO = CurrentIpoName.objects.get(id=IPOid, user=request.user)
        try:
            IPOPremium = float(IPO.Premium)
        except:
            IPOPremium = 0
        if IPO.ProfitMargin == None:
            IPO.ProfitMargin = 15
        if IPO.ExpecetdRetailApplication == None:
            IPO.ExpecetdRetailApplication = 2500000
        IPO.save()
        try:
            LotValue = float(IPO.IPOPrice)*float(IPO.LotSizeRetail)
            RetailSize = ((float(IPO.TotalIPOSzie))
                        * float(IPO.RetailPercentage))/100
            ApplicationFor1Time = (float(RetailSize)*10000000)/LotValue
        except:
            LotValue = 0
            RetailSize = 0
            ApplicationFor1Time = 0
        try:
            ProfitMargin = float(IPO.ProfitMargin)
        except:
            ProfitMargin = None
        try:
            ExpecetdRetailApplication = int(IPO.ExpecetdRetailApplication)
        except:
            ExpecetdRetailApplication = None
        try:
            NumberOfTimeIPO = ExpecetdRetailApplication/ApplicationFor1Time
        except:
            NumberOfTimeIPO = 0
        try:
            AvgShare = float(IPO.LotSizeRetail)/NumberOfTimeIPO
        except:
            AvgShare = 0
        if AvgShare > IPO.LotSizeRetail:
            AvgShare = IPO.LotSizeRetail
        try:
            BaseKostakRate = float(IPOPremium) * AvgShare
        except:
            BaseKostakRate = 0
        try:
            kostakRateForCustomer = BaseKostakRate - \
                ((BaseKostakRate*float(IPO.ProfitMargin))/100)
        except:
            kostakRateForCustomer = 0
        try:
            BaseSubjectToRate = float(IPOPremium) * float(IPO.LotSizeRetail)
        except:
            BaseSubjectToRate = 0
        try:
            SubjectToRateForCustomer = BaseSubjectToRate - \
                ((BaseSubjectToRate*float(IPO.ProfitMargin))/100)
        except:
            SubjectToRateForCustomer = 0

        order = Order.objects.filter(
            user=request.user, OrderIPOName_id=IPOid)
        Kostakentry = order.filter(OrderCategory="Kostak")
        NOBUYKostak = Kostakentry.filter(OrderType="BUY")
        NOBUYKostak11 = NOBUYKostak.aggregate(Sum('Quantity'))
        NOBUYKostak1 = NOBUYKostak11['Quantity__sum']
        if NOBUYKostak1 == None:
            CountofBUYKostak = 0
        else:
            CountofBUYKostak = NOBUYKostak1

        Kostakentry = order.filter(OrderCategory="Kostak")
        NOSELLKostak = Kostakentry.filter(OrderType="SELL")
        NOSELLKostak11 = NOSELLKostak.aggregate(Sum('Quantity'))
        NOSELLKostak1 = NOSELLKostak11['Quantity__sum']
        if NOSELLKostak1 == None:
            CountofSELLKostak = 0
        else:
            CountofSELLKostak = NOSELLKostak1

        try:
            CountOfKostak = CountofBUYKostak - CountofSELLKostak
        except:
            CountOfKostak = 0

        Kostakentry = order.filter(OrderCategory="Kostak")
        AmountBUYKostak = Kostakentry.filter(OrderType="BUY")
        AmountBUYKostak11 = AmountBUYKostak.aggregate(Sum('Amount'))
        AmountBUYKostak1 = AmountBUYKostak11['Amount__sum']
        if AmountBUYKostak1 == None:
            AmountofBUYKostak = 0
        else:
            AmountofBUYKostak = AmountBUYKostak1

        Kostakentry = order.filter(OrderCategory="Kostak")
        AmountSELLKostak = Kostakentry.filter(OrderType="SELL")
        AmountSELLKostak11 = AmountSELLKostak.aggregate(Sum('Amount'))
        AmountSELLKostak1 = AmountSELLKostak11['Amount__sum']
        if AmountSELLKostak1 == None:
            AmountofSELLKostak = 0
        else:
            AmountofSELLKostak = AmountSELLKostak1
        try:
            TotalKostakValue = AmountofBUYKostak + AmountofSELLKostak
        except:
            TotalKostakValue = 0
        try:
            KostakAvg = float(TotalKostakValue) / float(CountOfKostak)
        except:
            KostakAvg = 0

        SubjectToentry = order.filter(OrderCategory="Subject To")
        NOBUYSubjectTo = SubjectToentry.filter(OrderType="BUY")
        NOBUYSubjectTo11 = NOBUYSubjectTo.aggregate(Sum('Quantity'))
        NOBUYSubjectTo1 = NOBUYSubjectTo11['Quantity__sum']
        if NOBUYSubjectTo1 == None:
            CountofBUYSubjectTo = 0
        else:
            CountofBUYSubjectTo = NOBUYSubjectTo1

        SubjectToentry = order.filter(OrderCategory="Subject To")
        NOSELLSubjectTo = SubjectToentry.filter(OrderType="SELL")
        NOSELLSubjectTo11 = NOSELLSubjectTo.aggregate(Sum('Quantity'))
        NOSELLSubjectTo1 = NOSELLSubjectTo11['Quantity__sum']
        if NOSELLSubjectTo1 == None:
            CountofSELLSubjectTo = 0
        else:
            CountofSELLSubjectTo = NOSELLSubjectTo1

        try:
            CountOfSubjectTo = CountofBUYSubjectTo - CountofSELLSubjectTo
        except:
            CountOfSubjectTo = 0

        try:
            TotalApplication = CountOfKostak + CountOfSubjectTo
        except:
            TotalApplication = 0
        try:
            ShareTOBeSell = AvgShare * TotalApplication
        except:
            ShareTOBeSell = 0

        SubjectToentry = order.filter(OrderCategory="Subject To")
        AmountBUYSubjectTo = SubjectToentry.filter(OrderType="BUY")
        AmountBUYSubjectTo11 = AmountBUYSubjectTo.aggregate(Sum('Amount'))
        AmountBUYSubjectTo1 = AmountBUYSubjectTo11['Amount__sum']
        if AmountBUYSubjectTo1 == None:
            AmountofBUYSubjectTo = 0
        else:
            AmountofBUYSubjectTo = AmountBUYSubjectTo1

        SubjectToentry = order.filter(OrderCategory="Subject To")
        AmountSELLSubjectTo = SubjectToentry.filter(OrderType="SELL")
        AmountSELLSubjectTo11 = AmountSELLSubjectTo.aggregate(Sum('Amount'))
        AmountSELLSubjectTo1 = AmountSELLSubjectTo11['Amount__sum']
        if AmountSELLSubjectTo1 == None:
            AmountofSELLSubjectTo = 0
        else:
            AmountofSELLSubjectTo = AmountSELLSubjectTo1

        try:
            TotalSubjectToValue = AmountofBUYSubjectTo + AmountofSELLSubjectTo
        except:
            TotalSubjectToValue = 0
        try:

            SubjectToAvg = float(TotalSubjectToValue) / float(CountOfSubjectTo)
        except:
            SubjectToAvg = 0
        TotalCount = CountOfSubjectTo + CountOfKostak

        KostakShareQty = TotalCount * AvgShare

        Premiumentry = order.filter(OrderCategory="Premium")
        QTYBUYPremium = Premiumentry.filter(OrderType="BUY")
        QTYBUYPremium11 = QTYBUYPremium.aggregate(Sum('Quantity'))
        QTYBUYPremium1 = QTYBUYPremium11['Quantity__sum']
        if QTYBUYPremium1 == None:
            TotalBuyPremiumShareQty = 0
        else:
            TotalBuyPremiumShareQty = QTYBUYPremium1

        Premiumentry = order.filter(OrderCategory="Premium")
        QTYSELLPremium = Premiumentry.filter(OrderType="SELL")
        QTYSELLPremium11 = QTYSELLPremium.aggregate(Sum('Quantity'))
        QTYSELLPremium1 = QTYSELLPremium11['Quantity__sum']
        if QTYSELLPremium1 == None:
            TotalSellPremiumShareQty = 0
        else:
            TotalSellPremiumShareQty = QTYSELLPremium1
        try:
            n1 = (KostakAvg/AvgShare)/2
            n2 = (SubjectToAvg/float(IPO.LotSizeRetail))/2
            KostakShareAvg = n1 + n2
        except:
            KostakShareAvg = 0

        try:
            CountOfPremium = TotalBuyPremiumShareQty - TotalSellPremiumShareQty
        except:
            CountOfPremium = 0

        Premiumentry = order.filter(OrderCategory="Premium")
        AmountBUYPremium = Premiumentry.filter(OrderType="BUY")
        AmountBUYPremium11 = AmountBUYPremium.aggregate(Sum('Amount'))
        AmountBUYPremium1 = AmountBUYPremium11['Amount__sum']
        if AmountBUYPremium1 == None:
            TotalBuyPremiumShareAmount = 0
        else:
            TotalBuyPremiumShareAmount = AmountBUYPremium1

        Premiumentry = order.filter(OrderCategory="Premium")
        AmountSELLPremium = Premiumentry.filter(OrderType="SELL")
        AmountSELLPremium11 = AmountSELLPremium.aggregate(Sum('Amount'))
        AmountSELLPremium1 = AmountSELLPremium11['Amount__sum']
        if AmountSELLPremium1 == None:
            TotalSellPremiumShareAmount = 0
        else:
            TotalSellPremiumShareAmount = AmountSELLPremium1
        try:
            BuyPremiumShareAvg = float(
                TotalBuyPremiumShareAmount) / float(TotalBuyPremiumShareQty)
        except:
            BuyPremiumShareAvg = 0
        try:
            SellPremiumShareAvg = float(
                TotalSellPremiumShareAmount) / float(TotalSellPremiumShareQty)
        except:
            SellPremiumShareAvg = 0
        try:
            DiffereneQty = (TotalBuyPremiumShareQty+KostakShareQty) - \
                float(TotalSellPremiumShareQty)
        except:
            DiffereneQty = 0
        try:
            ProfitOrLoss = (SellPremiumShareAvg*TotalSellPremiumShareQty)-((KostakShareQty*KostakShareAvg)+(
                TotalBuyPremiumShareQty*BuyPremiumShareAvg)) + DiffereneQty*float(IPOPremium)
        except:
            ProfitOrLoss = 0
        return render(request, 'dashboard_sme.html', {'AvgShare': "{:.2f}".format(AvgShare), 'NumberOfTimeIPO': "{:.2f}".format(NumberOfTimeIPO), 'IpoPricePerShare': "{:.0f}".format(IPO.IPOPrice), 'ApplicationFor1Time': "{:.0f}".format(ApplicationFor1Time), 'CountofBUYKostak': "{:.2f}".format(CountofBUYKostak), 'CountofSELLKostak': "{:.2f}".format(CountofSELLKostak), 'CountOfKostak': "{:.2f}".format(CountOfKostak), 'KostakAvg': "{:.2f}".format(KostakAvg), 'CountofBUYSubjectTo': "{:.2f}".format(CountofBUYSubjectTo), 'CountofSELLSubjectTo': "{:.2f}".format(CountofSELLSubjectTo), 'CountOfSubjectTo': "{:.2f}".format(CountOfSubjectTo), 'SubjectToAvg': "{:.2f}".format(SubjectToAvg), 'KostakShareQty': "{:.2f}".format(KostakShareQty), 'TotalBuyPremiumShareQty': "{:.2f}".format(TotalBuyPremiumShareQty), 'TotalSellPremiumShareQty': "{:.2f}".format(TotalSellPremiumShareQty), 'CountOfPremium': "{:.2f}".format(CountOfPremium), 'IPOName': IPO, 'IPOid': IPOid, 'BaseKostakRate': "{:.2f}".format(BaseKostakRate), 'kostakRateForCustomer': "{:.2f}".format(kostakRateForCustomer), 'BaseSubjectToRate': "{:.2f}".format(BaseSubjectToRate), 'SubjectToRateForCustomer': "{:.2f}".format(SubjectToRateForCustomer), 'ExpecetdRetailApplication': ExpecetdRetailApplication, 'ProfitMargin': ProfitMargin, 'Premium': IPOPremium, 'ShareTOBeSell': "{:.2f}".format(ShareTOBeSell), 'KostakShareAvg': "{:.2f}".format(KostakShareAvg), 'BuyPremiumShareAvg': "{:.2f}".format(BuyPremiumShareAvg), 'SellPremiumShareAvg': "{:.2f}".format(SellPremiumShareAvg), 'DiffereneQty': "{:.2f}".format(DiffereneQty), 'ProfitOrLoss': "{:.0f}".format(ProfitOrLoss)})

    else:
        if value == 'B':

            retail = {}
            shni = {}
            bhni = {}

            IPO = IPOName
            try:
                IPOPremium = float(IPO.Premium)
                if IPOPremium == None:
                    IPOPremium = 0
            except:
                IPOPremium = 0
            if IPO.ProfitMargin == None:
                IPO.ProfitMargin = 15
            IPO.save()

            try:
                ProfitMargin = float(IPO.ProfitMargin)
            except:
                ProfitMargin = None

            try:
                Premium = float(IPO.Premium)
            except:
                Premium = None
            
            try:
                retail["BaseSubjectToRate"] = float(IPOPremium) * float(IPO.LotSizeRetail)
                shni["BaseSubjectToRate"] = float(IPOPremium) * float(IPO.LotSizeSHNI)
                bhni["BaseSubjectToRate"] = float(IPOPremium) * float(IPO.LotSizeBHNI)
            except:
                retail["BaseSubjectToRate"] = 0
                shni["BaseSubjectToRate"] = 0
                bhni["BaseSubjectToRate"] = 0
        
            try:
                retail['SubjectToRateForCustomer'] = retail["BaseSubjectToRate"] - \
                    ((retail["BaseSubjectToRate"]*float(IPO.ProfitMargin))/100)
                shni['SubjectToRateForCustomer'] = shni["BaseSubjectToRate"] - \
                    ((shni["BaseSubjectToRate"]*float(IPO.ProfitMargin))/100)
                bhni['SubjectToRateForCustomer'] = bhni["BaseSubjectToRate"] - \
                    ((bhni["BaseSubjectToRate"]*float(IPO.ProfitMargin))/100)
            except:
                retail['SubjectToRateForCustomer'] = 0
                shni['SubjectToRateForCustomer'] = 0
                bhni['SubjectToRateForCustomer'] = 0

            count = {}

            OrdCat = ['Kostak','SubjectTo']
            InvTyp = ['RETAIL','SHNI','BHNI']
            OrdTyp = ['BUY','SELL']
            products = Order.objects.filter(user=request.user, OrderIPOName_id=IPOid)
        
            aggregates = (
                products
                .values('OrderCategory', 'InvestorType', 'OrderType')
                .annotate(total_qty=Sum('Quantity'))
            )

            # Convert results into a lookup dictionary for fast access
            agg_lookup = {
                (row['OrderCategory'], row['InvestorType'], row['OrderType']): row['total_qty'] or 0
                for row in aggregates
            }

            for ordercategory in OrdCat:
                for investortype in InvTyp:    
                    for ordertype in OrdTyp:
                        cat_key = "Subject To" if ordercategory == "SubjectTo" else ordercategory
                        # if ordercategory == "SubjectTo":         
                        #     x = products.filter(OrderType=ordertype, OrderCategory="Subject To", InvestorType=investortype)
                        # else:
                        #     x = products.filter(OrderType=ordertype, OrderCategory=ordercategory, InvestorType=investortype)

                        count1 = agg_lookup.get((cat_key, investortype, ordertype), 0)
                    
                        if count1 == None:
                            count[f'{ordercategory}{investortype}{ordertype}Count'] = 0
                        else:
                            count[f'{ordercategory}{investortype}{ordertype}Count'] = count1

                    count[f'{ordercategory}{investortype}Net'] = count[f'{ordercategory}{investortype}BUYCount'] - count[f'{ordercategory}{investortype}SELLCount']
                
            # x = products.filter(OrderType="BUY", OrderCategory="Premium")

            PremiumBUY = agg_lookup.get(("Premium", "PREMIUM", "BUY"), 0)            
            if PremiumBUY == None:
                count['PremiumBUYCount'] = 0
            else:
                count['PremiumBUYCount'] = PremiumBUY

            # y = products.filter(OrderType="SELL", OrderCategory="Premium")

            PremiumSELL = agg_lookup.get(("Premium", "PREMIUM", "SELL"), 0)            
            if PremiumSELL == None:
                count['PremiumSELLCount'] = 0
            else:
                count['PremiumSELLCount'] = PremiumSELL

            count['PremiumNet'] = count['PremiumBUYCount'] - count['PremiumSELLCount']
            count['PremiumDiff'] = count['PremiumBUYCount'] - count['PremiumSELLCount']

            shares = {}

            shares['SELLTotal'] = 0
            shares['BUYTotal'] = 0
            Qtyfilter = OrderDetail.objects.filter(user = request.user, Order__OrderIPOName_id = IPOid)
        
            aggregated = (
                Qtyfilter
                .values(
                    'Order__OrderType',
                    'Order__InvestorType',
                    'Order__OrderCategory'
                )
                .annotate(total_alloted=Sum('AllotedQty'))
            )

            # Convert to dict for easy lookup
            agg_dict = {
                (row['Order__OrderCategory'], row['Order__InvestorType'], row['Order__OrderType']): row['total_alloted'] or 0
                for row in aggregated
            }
        
            for ordercategory in OrdCat:
                for investortype in InvTyp:    
                    buy_qty = agg_dict.get(
                        ("Subject To" if ordercategory == "SubjectTo" else ordercategory, investortype, "BUY"),
                        0
                    )
                    sell_qty = agg_dict.get(
                        ("Subject To" if ordercategory == "SubjectTo" else ordercategory, investortype, "SELL"),
                        0
                    )

                    shares[f"{ordercategory}{investortype}BUYShares"] = buy_qty
                    shares[f"{ordercategory}{investortype}SELLShares"] = sell_qty
                    shares[f"{ordercategory}{investortype}Net"] = buy_qty - sell_qty

                    shares['BUYTotal'] += buy_qty
                    shares['SELLTotal'] += sell_qty
            
            shares['Diff_Qty'] = shares['BUYTotal'] - shares['SELLTotal'] + count['PremiumDiff']

            AmountSum = products.aggregate(Sum('Amount'))['Amount__sum']        
            if AmountSum == None:
                AmountSum=0

            try:
                ExpectedProfitLoss = float(shares['Diff_Qty'])*float(IPO.Premium) + float(AmountSum)
            except:
                ExpectedProfitLoss = 0

            #RETAIL
            # y = Qtyfilter.filter(Order__OrderType="BUY", Order__InvestorType="RETAIL")
            # qty = y.aggregate(Sum('AllotedQty'))['AllotedQty__sum']    

            # if qty == None:
            #     shares['RETAILBUYAlloted'] = 0
            # else:
            #     shares['RETAILBUYAlloted'] = qty

            # z = Qtyfilter.filter(Order__OrderType="SELL", Order__InvestorType="RETAIL")
            # qtys = z.aggregate(Sum('AllotedQty'))['AllotedQty__sum']    

            # if qtys == None:
            #     shares['RETAILSELLAlloted'] = 0
            # else:
            #     shares['RETAILSELLAlloted'] = qtys

            # shares['RETAILAlloted'] = shares['RETAILBUYAlloted'] - shares['RETAILSELLAlloted']

            # #SHNI
            # y1 = Qtyfilter.filter(Order__OrderType="BUY", Order__InvestorType="SHNI")
            # qty = y1.aggregate(Sum('AllotedQty'))['AllotedQty__sum']    
        
            # if qty == None:
            #     shares[f'SHNIBUYAlloted'] = 0
            # else:
            #     shares[f'SHNIBUYAlloted'] = qty

            # z1 = Qtyfilter.filter(Order__OrderType="SELL", Order__InvestorType="SHNI")
            # qty1s = z1.aggregate(Sum('AllotedQty'))['AllotedQty__sum']    
        
            # if qty1s == None:
            #     shares[f'SHNISELLAlloted'] = 0
            # else:
            #     shares[f'SHNISELLAlloted'] = qty1s

            # shares['SHNIAlloted'] = shares['SHNIBUYAlloted'] - shares['SHNISELLAlloted']

            # #BHNI
            # y2 = Qtyfilter.filter(Order__OrderType="BUY", Order__InvestorType="BHNI")
            # qty2 = y2.aggregate(Sum('AllotedQty'))['AllotedQty__sum']    
        
            # if qty2 == None:
            #     shares[f'BHNIBUYAlloted'] = 0
            # else:
            #     shares[f'BHNIBUYAlloted'] = qty2

            # z2 = Qtyfilter.filter(Order__OrderType="SELL", Order__InvestorType="BHNI")
            # qty2s = z2.aggregate(Sum('AllotedQty'))['AllotedQty__sum']   
        
            # if qty2s == None:
            #     shares[f'BHNISELLAlloted'] = 0
            # else:
            #     shares[f'BHNISELLAlloted'] = qty2s
        
            for inv in ['RETAIL', 'SHNI', 'BHNI']:
                buy = sum(
                    row for key, row in agg_dict.items()
                    if key[1] == inv and key[2] == 'BUY'
                )
                sell = sum(
                    row for key, row in agg_dict.items()
                    if key[1] == inv and key[2] == 'SELL'
                )

                shares[f'{inv}BUYAlloted'] = buy
                shares[f'{inv}SELLAlloted'] = sell
                shares[f'{inv}Alloted'] = buy - sell

            shares['BHNIAlloted'] = shares['BHNIBUYAlloted'] - shares['BHNISELLAlloted']

            shares['ALLOTED'] = shares['RETAILAlloted'] + shares['SHNIAlloted'] + shares['BHNIAlloted']
            shares['ALLOTEDBUY'] = shares['RETAILBUYAlloted'] + shares['SHNIBUYAlloted'] + shares['BHNIBUYAlloted']
            shares['ALLOTEDSELL'] = shares['RETAILSELLAlloted'] + shares['SHNISELLAlloted'] + shares['BHNISELLAlloted']
        
            return render(request, 'Bdashboard.html', {'Premium':IPOPremium, 'ProfitMargin':ProfitMargin, 'retail':retail,'shni':shni,'bhni':bhni,'ExpectedProfitLoss':ExpectedProfitLoss,'shares':shares,'count':count, 'IPOName': IPO, 'IPOid': IPOid})
    
        if value == 'C':
            IPO = IPOName
    
            retail = {}
            shni = {}
            bhni = {}
            count = {}

            OrdCat = ['Kostak','SubjectTo']
            InvTyp = ['RETAIL','SHNI','BHNI']
            OrdTyp = ['BUY','SELL']
            products = Order.objects.filter(user=request.user, OrderIPOName_id=IPOid)
        
            aggregates = (
                products
                .values('OrderCategory', 'InvestorType', 'OrderType')
                .annotate(total_qty=Sum('Quantity'))
            )

            # Convert results into a lookup dictionary for fast access
            agg_lookup = {
                (row['OrderCategory'], row['InvestorType'], row['OrderType']): row['total_qty'] or 0
                for row in aggregates
            }

            for ordercategory in OrdCat:
                for investortype in InvTyp:    
                    for ordertype in OrdTyp:
                        cat_key = "Subject To" if ordercategory == "SubjectTo" else ordercategory
                        # if ordercategory == "SubjectTo":         
                        #     x = products.filter(OrderType=ordertype, OrderCategory="Subject To", InvestorType=investortype)
                        # else:
                        #     x = products.filter(OrderType=ordertype, OrderCategory=ordercategory, InvestorType=investortype)

                        count1 = agg_lookup.get((cat_key, investortype, ordertype), 0)
                    
                        if count1 == None:
                            count[f'{ordercategory}{investortype}{ordertype}Count'] = 0
                        else:
                            count[f'{ordercategory}{investortype}{ordertype}Count'] = count1

                    count[f'{ordercategory}{investortype}Net'] = count[f'{ordercategory}{investortype}BUYCount'] - count[f'{ordercategory}{investortype}SELLCount']
                
            # x = products.filter(OrderType="BUY", OrderCategory="Premium")

            PremiumBUY = agg_lookup.get(("Premium", "PREMIUM", "BUY"), 0)            
            if PremiumBUY == None:
                count['PremiumBUYCount'] = 0
            else:
                count['PremiumBUYCount'] = PremiumBUY

            # y = products.filter(OrderType="SELL", OrderCategory="Premium")

            PremiumSELL = agg_lookup.get(("Premium", "PREMIUM", "SELL"), 0)            
            if PremiumSELL == None:
                count['PremiumSELLCount'] = 0
            else:
                count['PremiumSELLCount'] = PremiumSELL

            count['PremiumNet'] = count['PremiumBUYCount'] - count['PremiumSELLCount']
            count['PremiumDiff'] = count['PremiumBUYCount'] - count['PremiumSELLCount']


            shares = {}
            Qtyfilter = OrderDetail.objects.filter(user = request.user, Order__OrderIPOName_id = IPOid)
        
            aggregated = (
                Qtyfilter
                .values(
                    'Order__OrderType',
                    'Order__InvestorType',
                    'Order__OrderCategory'
                )
                .annotate(total_alloted=Sum('AllotedQty'))
            )

            # Convert to dict for easy lookup
            agg_dict = {
                (row['Order__OrderCategory'], row['Order__InvestorType'], row['Order__OrderType']): row['total_alloted'] or 0
                for row in aggregated
            }

            shares['SELLTotal'] = 0
            shares['BUYTotal'] = 0
            for ordercategory in OrdCat:
                for investortype in InvTyp:    
                
                    buy_qty = agg_dict.get(
                        ("Subject To" if ordercategory == "SubjectTo" else ordercategory, investortype, "BUY"),
                        0
                    )
                    sell_qty = agg_dict.get(
                        ("Subject To" if ordercategory == "SubjectTo" else ordercategory, investortype, "SELL"),
                        0
                    )

                    shares[f"{ordercategory}{investortype}BUYShares"] = buy_qty
                    shares[f"{ordercategory}{investortype}SELLShares"] = sell_qty
                    shares[f"{ordercategory}{investortype}Net"] = buy_qty - sell_qty

                    shares['BUYTotal'] += buy_qty
                    shares['SELLTotal'] += sell_qty
                    # for ordertype in OrdTyp:
                    #     if ordercategory == "SubjectTo":
                    #         x = Qtyfilter.filter(Order__OrderType=ordertype, Order__InvestorType= investortype,Order__OrderCategory="Subject To")
                    #     else:
                    #         x = Qtyfilter.filter(Order__OrderType=ordertype, Order__InvestorType= investortype,Order__OrderCategory=ordercategory)

                    #     quantity = x.aggregate(Sum('AllotedQty'))['AllotedQty__sum']
                    
                    #     if quantity == None:
                    #         shares[f'{ordercategory}{investortype}{ordertype}Shares'] = 0
                    #     else:
                    #         shares[f'{ordercategory}{investortype}{ordertype}Shares'] = quantity

                    # shares['BUYTotal'] = shares['BUYTotal'] + shares[f'{ordercategory}{investortype}BUYShares'] 
                    # shares['SELLTotal'] = shares['SELLTotal'] + shares[f'{ordercategory}{investortype}SELLShares'] 
                    # shares[f'{ordercategory}{investortype}Net'] = shares[f'{ordercategory}{investortype}BUYShares'] - shares[f'{ordercategory}{investortype}SELLShares']
            
            shares['Diff_Qty'] = shares['BUYTotal'] - shares['SELLTotal'] + count['PremiumDiff']

            AmountSum = products.aggregate(Sum('Amount'))['Amount__sum']        
            if AmountSum == None:
                AmountSum=0

            try:
                ExpectedProfitLoss = float(AmountSum)
            except:
                ExpectedProfitLoss = 0

            #Alloted quantity Retail, shni, bhni 
            #RETAIL
            # y = Qtyfilter.filter(Order__OrderType="BUY", Order__InvestorType="RETAIL")
            # qty = y.aggregate(Sum('AllotedQty'))['AllotedQty__sum']    

            # if qty == None:
            #     shares['RETAILBUYAlloted'] = 0
            # else:
            #     shares['RETAILBUYAlloted'] = qty

            # z = Qtyfilter.filter(Order__OrderType="SELL", Order__InvestorType="RETAIL")
            # qtys = z.aggregate(Sum('AllotedQty'))['AllotedQty__sum']    

            # if qtys == None:
            #     shares['RETAILSELLAlloted'] = 0
            # else:
            #     shares['RETAILSELLAlloted'] = qtys

            # shares['RETAILAlloted'] = shares['RETAILBUYAlloted'] - shares['RETAILSELLAlloted']

            # #SHNI
            # y1 = Qtyfilter.filter(Order__OrderType="BUY", Order__InvestorType="SHNI")
            # qty = y1.aggregate(Sum('AllotedQty'))['AllotedQty__sum']    
        
            # if qty == None:
            #     shares[f'SHNIBUYAlloted'] = 0
            # else:
            #     shares[f'SHNIBUYAlloted'] = qty

            # z1 = Qtyfilter.filter(Order__OrderType="SELL", Order__InvestorType="SHNI")
            # qty1s = z1.aggregate(Sum('AllotedQty'))['AllotedQty__sum']    
        
            # if qty1s == None:
            #     shares[f'SHNISELLAlloted'] = 0
            # else:
            #     shares[f'SHNISELLAlloted'] = qty1s

            # shares['SHNIAlloted'] = shares['SHNIBUYAlloted'] - shares['SHNISELLAlloted']


            # #BHNI
            # y2 = Qtyfilter.filter(Order__OrderType="BUY", Order__InvestorType="BHNI")
            # qty2 = y2.aggregate(Sum('AllotedQty'))['AllotedQty__sum']    
        
            # if qty2 == None:
            #     shares[f'BHNIBUYAlloted'] = 0
            # else:
            #     shares[f'BHNIBUYAlloted'] = qty2

            # z2 = Qtyfilter.filter(Order__OrderType="SELL", Order__InvestorType="BHNI")
            # qty2s = z2.aggregate(Sum('AllotedQty'))['AllotedQty__sum']   
        
            # if qty2s == None:
            #     shares[f'BHNISELLAlloted'] = 0
            # else:
            #     shares[f'BHNISELLAlloted'] = qty2s
        
            for inv in ['RETAIL', 'SHNI', 'BHNI']:
                buy = sum(
                    row for key, row in agg_dict.items()
                    if key[1] == inv and key[2] == 'BUY'
                )
                sell = sum(
                    row for key, row in agg_dict.items()
                    if key[1] == inv and key[2] == 'SELL'
                )

                shares[f'{inv}BUYAlloted'] = buy
                shares[f'{inv}SELLAlloted'] = sell
                shares[f'{inv}Alloted'] = buy - sell

            shares['BHNIAlloted'] = shares['BHNIBUYAlloted'] - shares['BHNISELLAlloted']

            shares['ALLOTED'] = shares['RETAILAlloted'] + shares['SHNIAlloted'] + shares['BHNIAlloted']
            shares['ALLOTEDBUY'] = shares['RETAILBUYAlloted'] + shares['SHNIBUYAlloted'] + shares['BHNIBUYAlloted']
            shares['ALLOTEDSELL'] = shares['RETAILSELLAlloted'] + shares['SHNISELLAlloted'] + shares['BHNISELLAlloted']

            return render(request, 'Cdashboard.html', {'retail':retail,'shni':shni,'bhni':bhni,'ExpectedProfitLoss':ExpectedProfitLoss,'shares':shares,'count':count, 'IPOName': IPO, 'IPOid': IPOid})

        IPO = IPOName
        retail = {}
        shni = {}
        bhni = {}

        try:
            IPOPremium = float(IPO.Premium)
        except:
            IPOPremium = 0
        if IPO.ProfitMargin == None:
            IPO.ProfitMargin = 15
        if IPO.ExpecetdRetailApplication == '':
            IPO.ExpecetdRetailApplication = 2500000
        if IPO.ExpecetdSHNIApplication == None:
            IPO.ExpecetdSHNIApplication = 150000
        if IPO.ExpecetdBHNIApplication == None:
            IPO.ExpecetdBHNIApplication = 50000
        IPO.save()

        try:
            LotValueRetail = float(IPO.IPOPrice)*float(IPO.LotSizeRetail)
            RetailSize = ((float(IPO.TotalIPOSzie))
                        * float(IPO.RetailPercentage))/100
            retail["ApplicationFor1Time"] = (float(RetailSize)*10000000)/LotValueRetail

            LotValueSHNI = float(IPO.IPOPrice)*float(IPO.LotSizeSHNI)
            SHNISize = ((float(IPO.TotalIPOSzie))
                        * float(IPO.SHNIPercentage))/100
            shni["ApplicationFor1Time"] = (float(SHNISize)*10000000)/LotValueSHNI

            LotValueBHNI = float(IPO.IPOPrice)*float(IPO.LotSizeBHNI)
            BHNISize = ((float(IPO.TotalIPOSzie))
                        * float(IPO.BHNIPercentage))/100
            bhni["ApplicationFor1Time"] = (float(BHNISize)*10000000)/LotValueBHNI
        except:
            LotValueRetail = 0
            RetailSize = 0
            retail["ApplicationFor1Time"] = 0

            LotValueSHNI = 0
            SHNISize = 0
            shni["ApplicationFor1Time"] = 0

            LotValueBHNI = 0
            BHNISize = 0
            bhni["ApplicationFor1Time"] = 0
    
        try:
            ProfitMargin = float(IPO.ProfitMargin)
        except:
            ProfitMargin = None
    
        try:
            ExpecetdRetailApplication = int(IPO.ExpecetdRetailApplication)
            ExpecetdSHNIApplication = int(IPO.ExpecetdSHNIApplication)
            ExpecetdBHNIApplication = int(IPO.ExpecetdBHNIApplication)
        except:
            ExpecetdRetailApplication = None
            ExpecetdBHNIApplication = None
            ExpecetdSHNIApplication = None
    
        try:
            retail["NumberOfTimeIPO"] = ExpecetdRetailApplication/retail["ApplicationFor1Time"]
            shni["NumberOfTimeIPO"] = ExpecetdSHNIApplication/shni["ApplicationFor1Time"]
            bhni["NumberOfTimeIPO"] = ExpecetdBHNIApplication/bhni["ApplicationFor1Time"]
        except:
            retail["NumberOfTimeIPO"] = 0
            shni["NumberOfTimeIPO"] = 0
            bhni["NumberOfTimeIPO"] = 0
    
        try:
            retail["AvgShare"] = float(IPO.LotSizeRetail)/ retail["NumberOfTimeIPO"]
            shni["AvgShare"] = float(IPO.LotSizeSHNI)/shni["NumberOfTimeIPO"]
            bhni["AvgShare"] = float(IPO.LotSizeBHNI)/bhni["NumberOfTimeIPO"]
        except:
            retail["AvgShare"] = 0
            shni["AvgShare"] = 0
            bhni["AvgShare"] = 0
    
        if retail["AvgShare"] > IPO.LotSizeRetail:
            retail["AvgShare"] = IPO.LotSizeRetail
        if shni["AvgShare"] > IPO.LotSizeSHNI:
            shni["AvgShare"] = IPO.LotSizeSHNI
        if bhni["AvgShare"] > IPO.LotSizeBHNI:
            bhni["AvgShare"] = IPO.LotSizeBHNI

        try:
            retail["BaseKostakRate"] = float(IPOPremium) * retail['AvgShare']
            shni["BaseKostakRate"] = float(IPOPremium) * shni['AvgShare']
            bhni["BaseKostakRate"] = float(IPOPremium) * bhni['AvgShare']
        except:
            retail["BaseKostakRate"] = 0
            shni["BaseKostakRate"] = 0
            bhni["BaseKostakRate"] = 0

        try:
            retail['kostakRateForCustomer'] = retail["BaseKostakRate"] - \
                ((retail["BaseKostakRate"]*float(IPO.ProfitMargin))/100)
            shni['kostakRateForCustomer'] = shni["BaseKostakRate"] - \
                ((shni["BaseKostakRate"]*float(IPO.ProfitMargin))/100)
            bhni['kostakRateForCustomer'] = bhni["BaseKostakRate"] - \
                ((bhni["BaseKostakRate"]*float(IPO.ProfitMargin))/100)
        except:
            retail['kostakRateForCustomer'] = 0
            shni['kostakRateForCustomer'] = 0
            bhni['kostakRateForCustomer'] = 0

        try:
            retail["BaseSubjectToRate"] = float(IPOPremium) * float(IPO.LotSizeRetail)
            shni["BaseSubjectToRate"] = float(IPOPremium) * float(IPO.LotSizeSHNI)
            bhni["BaseSubjectToRate"] = float(IPOPremium) * float(IPO.LotSizeBHNI)
        except:
            retail["BaseSubjectToRate"] = 0
            shni["BaseSubjectToRate"] = 0
            bhni["BaseSubjectToRate"] = 0
    
        try:
            retail['SubjectToRateForCustomer'] = retail["BaseSubjectToRate"] - \
                ((retail["BaseSubjectToRate"]*float(IPO.ProfitMargin))/100)
            shni['SubjectToRateForCustomer'] = shni["BaseSubjectToRate"] - \
                ((shni["BaseSubjectToRate"]*float(IPO.ProfitMargin))/100)
            bhni['SubjectToRateForCustomer'] = bhni["BaseSubjectToRate"] - \
                ((bhni["BaseSubjectToRate"]*float(IPO.ProfitMargin))/100)
        except:
            retail['SubjectToRateForCustomer'] = 0
            shni['SubjectToRateForCustomer'] = 0
            bhni['SubjectToRateForCustomer'] = 0

        count = {}

        OrdCat = ['Kostak','SubjectTo']
        InvTyp = ['RETAIL','SHNI','BHNI']
        OrdTyp = ['BUY','SELL']
        products = Order.objects.filter(user=request.user, OrderIPOName_id=IPOid)
    
        aggregates = (
            products
            .values('OrderCategory', 'InvestorType', 'OrderType')
            .annotate(total_qty=Sum('Quantity'))
        )

        # Convert results into a lookup dictionary for fast access
        agg_lookup = {
            (row['OrderCategory'], row['InvestorType'], row['OrderType']): row['total_qty'] or 0
            for row in aggregates
        }

        for ordercategory in OrdCat:
            for investortype in InvTyp:    
                for ordertype in OrdTyp:
                    cat_key = "Subject To" if ordercategory == "SubjectTo" else ordercategory
                    # if ordercategory == "SubjectTo":         
                    #     x = products.filter(OrderType=ordertype, OrderCategory="Subject To", InvestorType=investortype)
                    # else:
                    #     x = products.filter(OrderType=ordertype, OrderCategory=ordercategory, InvestorType=investortype)

                    # count1 = x.aggregate(Sum('Quantity'))['Quantity__sum']
                    qty = agg_lookup.get((cat_key, investortype, ordertype), 0)
                    count[f"{ordercategory}{investortype}{ordertype}Count"] = qty
                
                    # if count1 == None:
                    #     count[f'{ordercategory}{investortype}{ordertype}Count'] = 0
                    # else:
                    #     count[f'{ordercategory}{investortype}{ordertype}Count'] = count1

                count[f'{ordercategory}{investortype}Net'] = count[f'{ordercategory}{investortype}BUYCount'] - count[f'{ordercategory}{investortype}SELLCount']
            
        # x = products.filter(OrderType="BUY", OrderCategory="Premium")

        PremiumBUY = agg_lookup.get(("Premium", "PREMIUM", "BUY"), 0)            
        if PremiumBUY == None:
            count['PremiumBUYCount'] = 0
        else:
            count['PremiumBUYCount'] = PremiumBUY

        # y = products.filter(OrderType="SELL", OrderCategory="Premium")

        PremiumSELL = agg_lookup.get(("Premium", "PREMIUM", "SELL"), 0)            
        if PremiumSELL == None:
            count['PremiumSELLCount'] = 0
        else:
            count['PremiumSELLCount'] = PremiumSELL

        count['PremiumNet'] = count['PremiumBUYCount'] - count['PremiumSELLCount']
        count['PremiumDiff'] = count['PremiumBUYCount'] - count['PremiumSELLCount']


        shares = {}
        shares['SELLTotal'] = 0
        shares['BUYTotal'] = 0
        for ordercategory in OrdCat:
            for investortype in InvTyp:    
                for ordertype in OrdTyp:
                    if investortype=="RETAIL":
                        shares[f'{ordercategory}{investortype}{ordertype}Shares'] = float(count[f'{ordercategory}{investortype}{ordertype}Count'])*float(retail['AvgShare']) 

                    if investortype=="SHNI":
                        shares[f'{ordercategory}{investortype}{ordertype}Shares'] = float(count[f'{ordercategory}{investortype}{ordertype}Count'])*float(shni['AvgShare']) 
                
                    if investortype=="BHNI":
                        shares[f'{ordercategory}{investortype}{ordertype}Shares'] = float(count[f'{ordercategory}{investortype}{ordertype}Count'])*float(bhni['AvgShare']) 

                shares['BUYTotal'] = shares['BUYTotal'] + shares[f'{ordercategory}{investortype}BUYShares'] 
                shares['SELLTotal'] = shares['SELLTotal'] + shares[f'{ordercategory}{investortype}SELLShares'] 
                shares[f'{ordercategory}{investortype}Net'] = shares[f'{ordercategory}{investortype}BUYShares'] - shares[f'{ordercategory}{investortype}SELLShares']
    
        shares['Diff_Qty'] = shares['BUYTotal'] - shares['SELLTotal'] + count['PremiumDiff']

        rate_data = (
            OrderDetail.objects
            .filter(user=request.user, Order__OrderIPOName_id=IPOid)
            .values('Order__OrderType')
            .annotate(total_rate=Sum('Order__Rate'))
        )
    
        rate_lookup = {item['Order__OrderType']: item['total_rate'] or 0 for item in rate_data}
    
        BuyRate = rate_lookup.get('BUY', 0)
        if BuyRate == None:
            BuyRate=0

        SellRate = rate_lookup.get('SELL', 0)
        if SellRate == None:
            SellRate=0

        try:
            ExpectedProfitLoss = float(shares['Diff_Qty'])*float(IPO.Premium) + float(SellRate) - float(BuyRate) 
        except:
            ExpectedProfitLoss = 0
    
        return render(request, 'dashboard.html', {'ExpectedProfitLoss':ExpectedProfitLoss, 'shares':shares,'count':count, 'retail':retail, 'shni':shni, 'bhni':bhni, 'IPOName': IPO, 'IPOid': IPOid, 'ExpecetdSHNIApplication': ExpecetdSHNIApplication, 'ExpecetdBHNIApplication': ExpecetdBHNIApplication, 'ExpecetdRetailApplication': ExpecetdRetailApplication, 'IpoPricePerShare': "{:.0f}".format(IPO.IPOPrice), 'ProfitMargin': ProfitMargin, 'Premium': IPOPremium})

@sync_to_async
def Od_DataUpdate_save(u_id,O_id,PreOpenPrice):
    orderdetail = OrderDetail(user=u_id, Order_id=O_id, PreOpenPrice=PreOpenPrice)
    orderdetail.save()

async def Od_DataUpdate(u_id,O_id,PreOpenPrice):
    await Od_DataUpdate_save(u_id,O_id,PreOpenPrice)

async def Order_Details_update(Qty,u_id,O_id,PreOpenPrice):
    tasks = []
    for i in range(int(Qty)):
        tasks.append(Od_DataUpdate(u_id,O_id,PreOpenPrice))

    await asyncio.gather(*tasks)

def Order_Details_update_sync(Qty, u_id, O_id, PreOpenPrice):
    async_to_sync(Order_Details_update)(Qty, u_id, O_id, PreOpenPrice)

@ allowed_users(allowed_roles=['Broker', 'Customer'])
def sell(request, IPOid,selectgroup=None):

    userid = request.user
    uid = request.user
    entry = GroupDetail.objects.filter(user=userid)
    IPOName = CurrentIpoName.objects.get(id=IPOid, user=userid)
    IPOType = IPOName.IPOType
    PreOpenPrice = IPOName.PreOpenPrice
    Ratelist = RateList(user=userid, RateListIPOName=IPOName, kostakSellRate=0, KostakSellQty=0, SubjecToSellRate=0, SubjecToSellQty=0,
                             PremiumSellRate=0, PremiumSellQty=0)

    product = Order.objects.filter(
            user=userid, OrderIPOName_id=IPOid).order_by('-id')

    if request.method == "POST":
        user = request.user
        Group = request.POST.get('item_id', '')
        gid = GroupDetail.objects.get(GroupName=Group, user=userid).id
        KostakRate = request.POST.get('KostakRate', '')
        SubjectToRate = request.POST.get('SubjectToRate', '')
        PremiumRate = request.POST.get('PremiumRate', '')
        KostakRateBHNI = request.POST.get('KostakRateBHNI', '')
        SubjectToRateBHNI = request.POST.get('SubjectToRateBHNI', '')   
        KostakRateSHNI = request.POST.get('KostakRateSHNI', '')
        SubjectToRateSHNI = request.POST.get('SubjectToRateSHNI', '')
        KostakQTY = request.POST.get('KostakQTY', '')
        SubjectToQTY = request.POST.get('SubjectToQTY', '')
        KostakQTYSHNI = request.POST.get('KostakQTYSHNI', '')
        SubjectToQTYSHNI = request.POST.get('SubjectToQTYSHNI', '')
        KostakQTYBHNI = request.POST.get('KostakQTYBHNI', '')
        SubjectToQTYBHNI = request.POST.get('SubjectToQTYBHNI', '')
        PremiumQTY = request.POST.get('PremiumQTY', '')   
    
        CallQty = request.POST.get('CallQTY', '')
        CallRate = request.POST.get('CallRate', '')
        CallStrikePrice = request.POST.get('CallStrikePrice', '')
    
        PutQTY = request.POST.get('PutQTY', '')
        PutRate = request.POST.get('PutRate', '')
        PutStrikePrice = request.POST.get('PutStrikePrice', '')
        placeOrderOnly = request.POST.get('placeOrderOnly', False)
        DateTime = request.POST.get('datetime', '')
        OrderDate = DateTime[0:10]
        OrderTime = DateTime[11:19]
    
    

        # Extract remark data from tags input and text field
        remark_tags_str = request.POST.get('remark_tags', '').strip()
        remark_text = request.POST.get('remark_text', '').strip()
    
        # Build remark JSON
        remark_json = {}
        if remark_tags_str:
            try:
                import json
                remark_tags = json.loads(remark_tags_str)
                if remark_tags:  # If there are any tags
                    remark_json['tags'] = remark_tags
            except json.JSONDecodeError:
                pass  # If JSON parsing fails, skip tags
    
        if remark_text:
            remark_json['text'] = remark_text
    
        # Set to None if empty
        remark_json = remark_json if remark_json else None

    
        a = 0

        if KostakQTY != '' and KostakQTY != "0" and KostakRate != '':
            order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType = 'RETAIL',
                          OrderCategory='Kostak', OrderType="SELL", Quantity=KostakQTY, Rate=KostakRate, OrderDate=OrderDate, OrderTime = OrderTime, remark=remark_json)
        
            O_limit  = CustomUser.objects.get( username = user)
    
            if O_limit.Order_limit is not None :
                BUY_Count = OrderDetail.objects.filter(user=user , Order__OrderIPOName_id= IPOid).count()
                Sum_Qty = int(BUY_Count) + int(KostakQTY)
                Limit  = int(O_limit.Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(request, f"You have reached the limit of {Limit} OrderDetail.")
                    return redirect(f'/{IPOid}/SELL')
            try:
                order.save()
                a = 1
                # Order_Details_update_sync(KostakQTY, uid, order.id, PreOpenPrice)
                # sync_to_async(Order_Details_update_sync)(KostakQTY, uid, order.id, PreOpenPrice)
                # asyncio.create_task(Order_Details_update(KostakQTY,uid,order.id,PreOpenPrice))

                orderdetails = [
                    OrderDetail(user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice)
                    for _ in range(int(KostakQTY))
                ]
                OrderDetail.objects.bulk_create(orderdetails)
            except:
                a=0
        
        if KostakQTYSHNI != '' and KostakQTYSHNI != "0" and KostakRateSHNI != '':
            order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType = 'SHNI',
                          OrderCategory='Kostak', OrderType="SELL", Quantity=KostakQTYSHNI, Rate=KostakRateSHNI, OrderDate=OrderDate, OrderTime = OrderTime, remark=remark_json)
        
            O_limit  = CustomUser.objects.get( username = user)
    
            if O_limit.Order_limit is not None :
                BUY_Count = OrderDetail.objects.filter(user=user , Order__OrderIPOName_id= IPOid).count()
                Sum_Qty = int(BUY_Count) + int(KostakQTYSHNI)
                Limit  = int(O_limit.Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(request, f"You have reached the limit of {Limit} OrderDetail.")
                    return redirect(f'/{IPOid}/SELL')
            try:    
                order.save()
                a = 1
            
                orderdetails = [
                    OrderDetail(user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice)
                    for _ in range(int(KostakQTYSHNI))
                ]
                OrderDetail.objects.bulk_create(orderdetails)
            except:
                a=0
    
        if KostakQTYBHNI != '' and KostakQTYBHNI != "0" and KostakRateBHNI != '':
            order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType = 'BHNI',
                          OrderCategory='Kostak', OrderType="SELL", Quantity=KostakQTYBHNI, Rate=KostakRateBHNI, OrderDate=OrderDate, OrderTime = OrderTime, remark=remark_json)
        
            O_limit  = CustomUser.objects.get( username = user)
    
            if O_limit.Order_limit is not None :
                BUY_Count = OrderDetail.objects.filter(user=user , Order__OrderIPOName_id= IPOid).count()
                Sum_Qty = int(BUY_Count) + int(KostakQTYBHNI)
                Limit  = int(O_limit.Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(request, f"You have reached the limit of {Limit} OrderDetail.")
                    return redirect(f'/{IPOid}/SELL')
            try:
                order.save()
                a = 1
                orderdetails = [
                    OrderDetail(user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice)
                    for _ in range(int(KostakQTYBHNI))
                ]
                OrderDetail.objects.bulk_create(orderdetails)
            except:
                a=0
    
        if SubjectToQTY != '' and SubjectToQTY != "0" and SubjectToRate!= '':
            if request.POST.get('subjectToIsPremiumRetail', '') != None and request.POST.get('subjectToIsPremiumRetail', '') != '' and request.POST.get('subjectToIsPremiumRetail', '') == 'on':
                order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType = 'RETAIL',
                             OrderCategory='Subject To', OrderType="SELL", Quantity=SubjectToQTY, Rate=SubjectToRate, OrderDate=OrderDate, OrderTime = OrderTime,Method = 'Premium', remark=remark_json)
            else:
                order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType = 'RETAIL',
                             OrderCategory='Subject To', OrderType="SELL", Quantity=SubjectToQTY, Rate=SubjectToRate, OrderDate=OrderDate, OrderTime = OrderTime, remark=remark_json)
             
            O_limit  = CustomUser.objects.get( username = user)
    
            if O_limit.Order_limit is not None :
                BUY_Count = OrderDetail.objects.filter(user=user , Order__OrderIPOName_id= IPOid).count()
                Sum_Qty = int(BUY_Count) + int(SubjectToQTY)
                Limit  = int(O_limit.Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(request, f"You have reached the limit of {Limit} OrderDetail.")
                    return redirect(f'/{IPOid}/SELL')
            try:
                order.save()
                a = 1
                orderdetails = [
                    OrderDetail(user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice)
                    for _ in range(int(SubjectToQTY))
                ]
                OrderDetail.objects.bulk_create(orderdetails)
            except:
                a=0
    
        if SubjectToQTYSHNI != '' and SubjectToQTYSHNI != "0" and SubjectToRateSHNI != '':
            if request.POST.get("subjectToIsPremiumSHNI",'') !=None and request.POST.get("subjectToIsPremiumSHNI",'') != '' and request.POST.get("subjectToIsPremiumSHNI",'') == 'on':
                order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType = 'SHNI',
                             OrderCategory='Subject To', OrderType="SELL", Quantity=SubjectToQTYSHNI, Rate=SubjectToRateSHNI, OrderDate=OrderDate, OrderTime = OrderTime,Method = 'Premium', remark=remark_json)
            else:
                order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType = 'SHNI',
                             OrderCategory='Subject To', OrderType="SELL", Quantity=SubjectToQTYSHNI, Rate=SubjectToRateSHNI, OrderDate=OrderDate, OrderTime = OrderTime, remark=remark_json)
        
            O_limit  = CustomUser.objects.get( username = user)
    
            if O_limit.Order_limit is not None :
                BUY_Count = OrderDetail.objects.filter(user=user , Order__OrderIPOName_id= IPOid).count()
                Sum_Qty = int(BUY_Count) + int(SubjectToQTYBHNI)
                Limit  = int(O_limit.Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(request, f"You have reached the limit of {Limit} OrderDetail.")
                    return redirect(f'/{IPOid}/SELL')
            try:
                order.save()
                a = 1
                orderdetails = [
                    OrderDetail(user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice)
                    for _ in range(int(SubjectToQTYSHNI))
                ]
                OrderDetail.objects.bulk_create(orderdetails)
            except:
                a=0
    
        if SubjectToQTYBHNI != '' and SubjectToQTYBHNI != "0" and SubjectToRateBHNI != '':
            if request.POST.get("subjectToIsPremiumBHNI",'') !=None and request.POST.get("subjectToIsPremiumBHNI",'') != '' and request.POST.get("subjectToIsPremiumBHNI",'') == 'on':
                order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType = 'BHNI',
                             OrderCategory='Subject To', OrderType="SELL", Quantity=SubjectToQTYBHNI, Rate=SubjectToRateBHNI, OrderDate=OrderDate, OrderTime = OrderTime,Method = 'Premium', remark=remark_json)
            else:
                order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType = 'BHNI',
                         OrderCategory='Subject To', OrderType="SELL", Quantity=SubjectToQTYBHNI, Rate=SubjectToRateBHNI, OrderDate=OrderDate, OrderTime = OrderTime, remark=remark_json)
        
            O_limit  = CustomUser.objects.get( username = user)
    
            if O_limit.Order_limit is not None :
                BUY_Count = OrderDetail.objects.filter(user=user , Order__OrderIPOName_id= IPOid).count()
                Sum_Qty = int(BUY_Count) + int(SubjectToQTYBHNI)
                Limit  = int(O_limit.Order_limit)

                if BUY_Count >= Limit + 1:
                    messages.error(request, f"You have reached the limit of {Limit} OrderDetail.")
                    return redirect(f'/{IPOid}/SELL')
            try:
                order.save()
                a = 1
                orderdetails = [
                    OrderDetail(user=uid, Order_id=order.id, PreOpenPrice=PreOpenPrice)
                    for _ in range(int(SubjectToQTYBHNI))
                ]
                OrderDetail.objects.bulk_create(orderdetails)
            except:
                a=0
    
        if PremiumQTY != '' and PremiumQTY != "0" and PremiumRate != '':
            order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType ='PREMIUM',
                            OrderCategory='Premium', OrderType="SELL", Quantity=PremiumQTY, Rate=PremiumRate, OrderDate=OrderDate, OrderTime = OrderTime, remark=remark_json)
        
            PRI_limit  = CustomUser.objects.get( username = user)
        
            if PRI_limit.Premium_Order_limit is not None :
                Order_type = "Premium"
                Pri_QTY = Order.objects.filter(user=user , OrderIPOName_id= IPOid , OrderCategory=Order_type).aggregate(Sum('Quantity'))['Quantity__sum']
                Pri_QTY = Pri_QTY if Pri_QTY is not None else 0
                Sum_Qty = int(Pri_QTY) + int(PremiumQTY)
                Limit  = int(PRI_limit.Premium_Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(request, f"You have reached the limit of {Limit} Premium shares QTY.")
                    return redirect(f'/{IPOid}/SELL')
            try:
                order.save()
                entry2 = Order.objects.get(user=request.user, id=order.id)
                calculate(IPOid, request.user,entry2.id)
                a = 1
            except:
                a=0
    
        if CallQty != '' and CallQty != "0" and CallRate != '' and CallStrikePrice != '':
            order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType ='OPTIONS',
                    OrderCategory='CALL', OrderType="SELL", Quantity=CallQty, Rate=CallRate, OrderDate=OrderDate, OrderTime = OrderTime,Method=CallStrikePrice, remark=remark_json)
        
            O_limit  = CustomUser.objects.get( username = user)
            if O_limit.Premium_Order_limit is not None :
                Order_type = "Premium"
                Pri_QTY = Order.objects.filter(user=user , OrderIPOName_id= IPOid , OrderCategory=Order_type).aggregate(Sum('Quantity'))['Quantity__sum'] 
                Pri_QTY = Pri_QTY if Pri_QTY is not None else 0
                Sum_Qty = int(Pri_QTY) + int(PremiumQTY)
                Limit  = int(O_limit.Premium_Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(request, f"You have reached the limit of {Limit} Premium shares QTY.")
                    return redirect(f'/{IPOid}/SELL')
            
            try:
                order.save()
                entry2 = Order.objects.get(user=request.user, id=order.id)
                calculate(IPOid, request.user,entry2.id)
                a = 1
            except:
                a==0
            
        if PutQTY != '' and PutQTY != "0" and PutRate != '' and PutStrikePrice != '':
            order = Order(user=uid, OrderGroup_id=gid, OrderIPOName=IPOName, InvestorType ='OPTIONS',
                    OrderCategory='PUT', OrderType="SELL", Quantity=PutQTY, Rate=PutRate, OrderDate=OrderDate, OrderTime = OrderTime,Method=PutStrikePrice, remark=remark_json)
        
            O_limit  = CustomUser.objects.get( username = user)
            if O_limit.Premium_Order_limit is not None :
                Order_type = "Premium"
                Pri_QTY = Order.objects.filter(user=user , OrderIPOName_id= IPOid , OrderCategory=Order_type).aggregate(Sum('Quantity'))['Quantity__sum'] 
                Pri_QTY = Pri_QTY if Pri_QTY is not None else 0
                Sum_Qty = int(Pri_QTY) + int(PremiumQTY)
                Limit  = int(O_limit.Premium_Order_limit)

                if Sum_Qty >= Limit + 1:
                    messages.error(request, f"You have reached the limit of {Limit} Premium shares QTY.")
                    return redirect(f'/{IPOid}/SELL')
            
            try:
                order.save()
                entry2 = Order.objects.get(user=request.user, id=order.id)
                calculate(IPOid, request.user,entry2.id)
                a = 1
            except:
                a==0
        if a == 1:
            if placeOrderOnly:
                messages.success(request, 'Sell order placed successfully.')
            else:
                messages.success(request, 'Sell order placed successfully. Telegram message sent successfully ')
            return JsonResponse({'status':'success','message':'SELL order placed successfully'})
            # return render(request, 'sell.html')
        
        else:
            messages.error(request, 'Sell order was not placed. Please try again.')
            return JsonResponse({'status':'error','message':'SELL order dose not placed'})
        

    if selectgroup!=None:
        selectgroup=unquote(selectgroup)
    else:
        if Order.objects.count() > 0:
            selectgroup = Order.objects.latest('id').OrderGroup.GroupName
        else:
            selectgroup = None

    return render(request, 'sell.html', {'product':product,'Group': entry.order_by('GroupName'), 'Ratelist': Ratelist, 'IPOName': IPOName, 'IPOid': IPOid,"order_type": "SELL", 'selectgroup': selectgroup})

#order fun
@ allowed_users(allowed_roles=['Broker', 'Customer'])
def OrderFunction(request, IPOid):
    if request.user.groups.all()[0].name == 'Broker':
        userid = request.user
        products = Order.objects.filter(
            user=userid, OrderIPOName_id=IPOid)
    else:
        userid = request.user.Broker_id
        products = Order.objects.filter(
            user=userid, OrderIPOName_id=IPOid, OrderGroup_id=request.user.Group_id)
    IPO = CurrentIpoName.objects.get(id=IPOid, user=userid)
    Group = GroupDetail.objects.filter(user=userid)
    Groupfilter = 'All'
    OrderCategoryFilter = 'All'
    InvestorTypeFilter = 'All'

    OrdCat = ['Kostak','SubjectTo','CALL','PUT']
    InvTyp = ['RETAIL','SHNI','BHNI','OPTIONS']
    OrdTyp = ['BUY','SELL']

    strike_dict = {}
    dict_count = {}
    dict_avg = {}
    dict_amount = {}

    if request.method == "POST":
        Groupfilter = request.POST.get('Groupfilter', 'All')
        OrderCategoryFilter = request.POST.get('OrderCategoryFilter', 'All')
        InvestorTypeFilter = request.POST.get('InvestorTypeFilter', 'All')

    # Validate and apply filters
    if is_valid_queryparam(Groupfilter) and Groupfilter != 'All':
        products = products.filter(OrderGroup__GroupName=Groupfilter)
    if is_valid_queryparam(OrderCategoryFilter) and OrderCategoryFilter != 'All':
        products = products.filter(OrderCategory=OrderCategoryFilter)
    if is_valid_queryparam(InvestorTypeFilter) and InvestorTypeFilter != 'All':
        products = products.filter(InvestorType=InvestorTypeFilter)

    aggregates = (
        products
        .values("OrderType", "OrderCategory", "InvestorType", "Method")
        .annotate(
            total_qty=Sum("Quantity"),
            total_amt=Sum(F("Rate") * F("Quantity")),
            total_count=Count("id")
        )
    )

    agg_lookup = {}
    for row in aggregates:
        key = (row["OrderCategory"], row["InvestorType"], row["OrderType"], row["Method"])
        agg_lookup[key] = {
            "count": row["total_qty"] or 0,
            "amount": row["total_amt"] or 0,
            "entries": row["total_count"] or 0,
        }

    for ordertype in OrdTyp:
        for ordercategory in OrdCat:
            for investortype in InvTyp:
                key_category = "Subject To" if ordercategory == "SubjectTo" else ordercategory
                dict_key_prefix = f"{ordercategory}{investortype}{ordertype}"

                # Lookup (we don’t hit DB here)
                # NOTE: Method could vary (Premium/Normal/Strike etc.), so we loop over methods in agg_lookup
                matching_rows = [
                    v for k, v in agg_lookup.items()
                    if k[0] == key_category and k[1] == investortype and k[2] == ordertype
                ]

                # Aggregate amounts manually (still in memory, not DB)
                total_count = sum(v["count"] for v in matching_rows)
                total_amount = 0

                for (cat, inv, ot, method), v in agg_lookup.items():
                    if cat == key_category and inv == investortype and ot == ordertype:
                        # Apply your "Subject To" premium logic here
                        if cat == "Subject To" and method == "Premium":
                            if investortype == "RETAIL":
                                lot_size = IPO.LotSizeRetail
                            elif investortype == "SHNI":
                                lot_size = IPO.LotSizeSHNI
                            elif investortype == "BHNI":
                                lot_size = IPO.LotSizeBHNI
                            else:
                                lot_size = 1
                            total_amount += (lot_size * v["amount"])
                        elif investortype == "OPTIONS" and ordercategory in ["CALL", "PUT"]:
                        
                            strike = method or "NA"

                            # Initialize dict structure
                            if strike not in strike_dict:
                                strike_dict[strike] = {
                                    "CALL": {"BUY": {"count":0,"amount":0,"avg":0,"net":0},
                                            "SELL":{"count":0,"amount":0,"avg":0 ,"net":0}},
                                    "PUT":  {"BUY": {"count":0,"amount":0,"avg":0 ,"net":0},
                                            "SELL":{"count":0,"amount":0,"avg":0 ,"net":0}}
                                }
                            # Update values
                            # strike_dict[strike][ordercategory][ordertype]["count"] += v.Quantity
                            # strike_dict[strike][ordercategory][ordertype]["amount"] += (v.Rate * v.Quantity)
                            strike_dict[strike][ordercategory][ordertype]["count"] += v["count"]
                            strike_dict[strike][ordercategory][ordertype]["amount"] += v["amount"]

                            # Calculate average
                            c = strike_dict[strike][ordercategory][ordertype]["count"]
                            a = strike_dict[strike][ordercategory][ordertype]["amount"]
                            strike_dict[strike][ordercategory][ordertype]["avg"] = (a / c) if c else 0
                        
                            # Net = (BUY amount - SELL amount) for that side
                            buy_amt  = strike_dict[strike][ordercategory]["BUY"]["amount"]
                            sell_amt = strike_dict[strike][ordercategory]["SELL"]["amount"]
                            strike_dict[strike][ordercategory]["BUY"]["net"]  = buy_amt - sell_amt
                            strike_dict[strike][ordercategory]["SELL"]["net"] = sell_amt - buy_amt
                        
                            # amount = (v.Rate * v.Quantity) + amount
                            total_amount += v["amount"]
                        else:
                            total_amount += v["amount"]

                # Save into dicts
                dict_count[f"{dict_key_prefix}Count"] = total_count
                dict_avg[f"{dict_key_prefix}Avg"] = (total_amount / total_count) if total_count else 0
                dict_amount[f"{dict_key_prefix}Amount"] = total_amount
        
    net_count = {}
    net_avg = {}
    net_amount = {}
            
    for ordercategory in OrdCat:
        for investortype in InvTyp:
            # Keys for BUY and SELL
            buy_key_count = f"{ordercategory}{investortype}BUYCount"
            sell_key_count = f"{ordercategory}{investortype}SELLCount"
        
            buy_key_avg = f"{ordercategory}{investortype}BUYAvg"
            sell_key_avg = f"{ordercategory}{investortype}SELLAvg"

            # Get counts (default 0 if missing)
            buy_count = dict_count.get(buy_key_count, 0)
            sell_count = dict_count.get(sell_key_count, 0)
            net_c = buy_count - sell_count

            # Get amounts (Count * Avg)
            buy_amount = buy_count * dict_avg.get(buy_key_avg, 0)
            sell_amount = sell_count * dict_avg.get(sell_key_avg, 0)
            net_amt = buy_amount - sell_amount

            # Calculate net average
            if net_c != 0:
                net_a = net_amt / net_c
            else:
                net_a = 0
            
            if net_c == 0:
                net_amt = sell_amount - buy_amount

            # Store results
            key_prefix = f"{ordercategory}{investortype}Net"
            net_count[f"{key_prefix}Count"] = net_c
            net_avg[f"{key_prefix}Avg"] = round(net_a, 2)
            net_amount[f"{key_prefix}Amount"] = round(net_amt, 2)
        
    product = products.order_by('-OrderDate','-OrderTime')

    PremiumBuyfilter = products.filter(OrderType="BUY",OrderCategory="Premium")
    # PremiumBuyCount11 = PremiumBuyfilter.aggregate(Sum('Quantity'))
    matching_rows = [
        v for k, v in agg_lookup.items()
        if k[0] == "Premium" and k[1] == "PREMIUM" and k[2] == "BUY"
    ]
    PremiumBuyCount1 = sum(v["count"] for v in matching_rows)
    if PremiumBuyCount1 == None:
        PremiumBuyCount = 0
    else:
        PremiumBuyCount = PremiumBuyCount1

    PremiumBuyAmount=0
    for i in PremiumBuyfilter:
        PremiumBuyAmount=(i.Quantity*i.Rate)+PremiumBuyAmount

    if PremiumBuyCount==0:
        PremiumBuyAvg=0    
    else:
        PremiumBuyAvg=PremiumBuyAmount/PremiumBuyCount

    PremiumSellfilter = products.filter(OrderType="SELL",OrderCategory="Premium")
    # PremiumSellCount11 = PremiumSellfilter.aggregate(Sum('Quantity'))
    matching_rows = [
        v for k, v in agg_lookup.items()
        if k[0] == "Premium" and k[1] == "PREMIUM" and k[2] == "SELL"
    ]
    PremiumSellCount1 = sum(v["count"] for v in matching_rows)
    if PremiumSellCount1 == None:
        PremiumSellCount = 0
    else:
        PremiumSellCount = PremiumSellCount1

    PremiumSellAmount=0
    for i in PremiumSellfilter:
        PremiumSellAmount=(i.Quantity*i.Rate)+PremiumSellAmount

    if PremiumSellCount==0:
        PremiumSellAvg=0    
    else:
        PremiumSellAvg=PremiumSellAmount/PremiumSellCount

    PremiumNetCount = PremiumBuyCount - PremiumSellCount
    Premiumavg1 = PremiumBuyCount * PremiumBuyAvg
    Premiumavg2 = PremiumSellCount * PremiumSellAvg
    pri_net_avg = Premiumavg1 - Premiumavg2
    if PremiumNetCount != 0:
        PremiumNetAvg = pri_net_avg /PremiumNetCount
        PremiumNetAmount = PremiumBuyAmount - PremiumSellAmount
    else:
        PremiumNetAvg =  0
        PremiumNetAmount = PremiumSellAmount - PremiumBuyAmount
    
    if request.method == "POST":
        strike_dict = {}
        Groupfilter = request.POST.get('Groupfilter', 'All')
        OrderCategoryFilter = request.POST.get('OrderCategoryFilter', 'All')
        InvestorTypeFilter = request.POST.get('InvestorTypeFilter', 'All')
    
        if InvestorTypeFilter == '' or InvestorTypeFilter == None:
            InvestorTypeFilter = 'All'
        
        if Groupfilter == '' or Groupfilter == None:
            Groupfilter = 'All'
        
        if OrderCategoryFilter == '' or OrderCategoryFilter == None:
            OrderCategoryFilter = 'All'
    
        if is_valid_queryparam(Groupfilter) and Groupfilter != 'All':
            products = products.filter(OrderGroup__GroupName=Groupfilter)
        if is_valid_queryparam(OrderCategoryFilter) and OrderCategoryFilter != 'All':
            products = products.filter(OrderCategory=OrderCategoryFilter)
        if is_valid_queryparam(InvestorTypeFilter) and InvestorTypeFilter != 'All':
            products = products.filter(InvestorType=InvestorTypeFilter)
        Groupfilter = Groupfilter
        OrderCategoryFilter = OrderCategoryFilter
        InvestorTypeFilter = InvestorTypeFilter

        aggregates = (
            products
            .values("OrderType", "OrderCategory", "InvestorType", "Method")
            .annotate(
                total_qty=Sum("Quantity"),
                total_amt=Sum(F("Rate") * F("Quantity")),
                total_count=Count("id")
            )
        )
    
        agg_lookup = {}
        for row in aggregates:
            key = (row["OrderCategory"], row["InvestorType"], row["OrderType"], row["Method"])
            agg_lookup[key] = {
                "count": row["total_qty"] or 0,
                "amount": row["total_amt"] or 0,
                "entries": row["total_count"] or 0,
            }
        for ordertype in OrdTyp:
            for ordercategory in OrdCat:
            # for investortype in InvTyp:
                for investortype in InvTyp:
                    key_category = "Subject To" if ordercategory == "SubjectTo" else ordercategory
                    dict_key_prefix = f"{ordercategory}{investortype}{ordertype}"

                    # Lookup (we don’t hit DB here)
                    # NOTE: Method could vary (Premium/Normal/Strike etc.), so we loop over methods in agg_lookup
                    matching_rows = [
                        v for k, v in agg_lookup.items()
                        if k[0] == key_category and k[1] == investortype and k[2] == ordertype
                    ]

                    # Aggregate amounts manually (still in memory, not DB)
                    total_count = sum(v["count"] for v in matching_rows)
                    total_amount = 0

                    for (cat, inv, ot, method), v in agg_lookup.items():
                        if cat == key_category and inv == investortype and ot == ordertype:
                            # Apply your "Subject To" premium logic here
                            if cat == "Subject To" and method == "Premium":
                                if investortype == "RETAIL":
                                    lot_size = IPO.LotSizeRetail
                                elif investortype == "SHNI":
                                    lot_size = IPO.LotSizeSHNI
                                elif investortype == "BHNI":
                                    lot_size = IPO.LotSizeBHNI
                                else:
                                    lot_size = 1
                                total_amount += (lot_size * v["amount"])
                            elif investortype == "OPTIONS" and ordercategory in ["CALL", "PUT"]:
                        
                                strike = method or "NA"

                                # Initialize dict structure
                                if strike not in strike_dict:
                                    strike_dict[strike] = {
                                        "CALL": {"BUY": {"count":0,"amount":0,"avg":0,"net":0},
                                                "SELL":{"count":0,"amount":0,"avg":0 ,"net":0}},
                                        "PUT":  {"BUY": {"count":0,"amount":0,"avg":0 ,"net":0},
                                                "SELL":{"count":0,"amount":0,"avg":0 ,"net":0}}
                                    }
                                # Update values
                                # strike_dict[strike][ordercategory][ordertype]["count"] += v.Quantity
                                # strike_dict[strike][ordercategory][ordertype]["amount"] += (v.Rate * v.Quantity)
                                strike_dict[strike][ordercategory][ordertype]["count"] += v["count"]
                                strike_dict[strike][ordercategory][ordertype]["amount"] += v["amount"]

                                # Calculate average
                                c = strike_dict[strike][ordercategory][ordertype]["count"]
                                a = strike_dict[strike][ordercategory][ordertype]["amount"]
                                strike_dict[strike][ordercategory][ordertype]["avg"] = (a / c) if c else 0
                            
                                # Net = (BUY amount - SELL amount) for that side
                                buy_amt  = strike_dict[strike][ordercategory]["BUY"]["amount"]
                                sell_amt = strike_dict[strike][ordercategory]["SELL"]["amount"]
                                strike_dict[strike][ordercategory]["BUY"]["net"]  = buy_amt - sell_amt
                                strike_dict[strike][ordercategory]["SELL"]["net"] = sell_amt - buy_amt
                            
                                # amount = (v.Rate * v.Quantity) + amount
                                total_amount += v["amount"]
                            else:
                                total_amount += v["amount"]

                    # Save into dicts
                    dict_count[f"{dict_key_prefix}Count"] = total_count
                    dict_avg[f"{dict_key_prefix}Avg"] = (total_amount / total_count) if total_count else 0
                    dict_amount[f"{dict_key_prefix}Amount"] = total_amount
            
        for ordercategory in OrdCat:
            for investortype in InvTyp:
                # Keys for BUY and SELL
                buy_key_count = f"{ordercategory}{investortype}BUYCount"
                sell_key_count = f"{ordercategory}{investortype}SELLCount"
            
                buy_key_avg = f"{ordercategory}{investortype}BUYAvg"
                sell_key_avg = f"{ordercategory}{investortype}SELLAvg"

                # Get counts (default 0 if missing)
                buy_count = dict_count.get(buy_key_count, 0)
                sell_count = dict_count.get(sell_key_count, 0)
                net_c = buy_count - sell_count

                # Get amounts (Count * Avg)
                buy_amount = buy_count * dict_avg.get(buy_key_avg, 0)
                sell_amount = sell_count * dict_avg.get(sell_key_avg, 0)
                net_amt = buy_amount - sell_amount

                # Calculate net average
                if net_c != 0:
                    net_a = net_amt / net_c
                else:
                    net_a = 0
                
                if net_c == 0:
                    net_amt = sell_amount - buy_amount
                # Store results
                key_prefix = f"{ordercategory}{investortype}Net"
                net_count[f"{key_prefix}Count"] = net_c
                net_avg[f"{key_prefix}Avg"] = round(net_a, 2)
                net_amount[f"{key_prefix}Amount"] = round(net_amt, 2)
            
        product = products.order_by('-OrderDate','-OrderTime')
    
        # PremiumBuyfilter = products.filter(OrderType="BUY",OrderCategory="Premium")
        # PremiumBuyCount11 = PremiumBuyfilter.aggregate(Sum('Quantity'))
        matching_rows = [
            v for k, v in agg_lookup.items()
            if k[0] == "Premium" and k[1] == "PREMIUM" and k[2] == "BUY"
        ]
        PremiumBuyCount1 = sum(v["count"] for v in matching_rows)
        if PremiumBuyCount1 == None:
            PremiumBuyCount = 0
        else:
            PremiumBuyCount = PremiumBuyCount1
    
        PremiumBuyAmount=0
        for i in PremiumBuyfilter:
            PremiumBuyAmount=(i.Quantity*i.Rate)+PremiumBuyAmount

        if PremiumBuyCount==0:
            PremiumBuyAvg=0    
        else:
            PremiumBuyAvg=PremiumBuyAmount/PremiumBuyCount
    
        PremiumSellfilter = products.filter(OrderType="SELL",OrderCategory="Premium")
        PremiumSellCount11 = PremiumSellfilter.aggregate(Sum('Quantity'))
        PremiumSellCount1 = PremiumSellCount11['Quantity__sum']
        if PremiumSellCount1 == None:
            PremiumSellCount = 0
        else:
            PremiumSellCount = PremiumSellCount1

        PremiumSellAmount=0
        for i in PremiumSellfilter:
            PremiumSellAmount=(i.Quantity*i.Rate)+PremiumSellAmount

        if PremiumSellCount==0:
            PremiumSellAvg=0    
        else:
            PremiumSellAvg=PremiumSellAmount/PremiumSellCount
    
        PremiumNetCount = PremiumBuyCount - PremiumSellCount
        Premiumavg1 = PremiumBuyCount * PremiumBuyAvg
        Premiumavg2 = PremiumSellCount * PremiumSellAvg
        pri_net_avg = Premiumavg1 - Premiumavg2
        if PremiumNetCount != 0:
            PremiumNetAvg = pri_net_avg / PremiumNetCount
            PremiumNetAmount = PremiumBuyAmount - PremiumSellAmount
        else:
            PremiumNetAvg =  0
            PremiumNetAmount = PremiumSellAmount - PremiumBuyAmount
        

    strike_prices = []
    grand_call_count = grand_call_amount = grand_put_count = grand_put_amount = 0
    for strike, cats in strike_dict.items():
        # CALL
        call_buy_count = cats["CALL"]["BUY"]["count"]
        call_sell_count = cats["CALL"]["SELL"]["count"]
        call_buy_amount = cats["CALL"]["BUY"]["amount"]
        call_sell_amount = cats["CALL"]["SELL"]["amount"]

    
        call_net_count = call_buy_count - call_sell_count
        call_avg1 = call_buy_amount - call_sell_amount
        call_avg2 = call_sell_amount - call_buy_amount
        call_net_avg = call_avg1 - call_avg2
        # call_net_amount = call_buy_amount - call_sell_amount
        if call_net_count != 0:
            call_avg = call_net_avg / call_net_count
            call_net_amount = call_buy_amount - call_sell_amount
        else:
            call_avg = 0
            call_net_amount = call_sell_amount - call_buy_amount
    
        # PUT
        put_buy_count = cats["PUT"]["BUY"]["count"]
        put_sell_count = cats["PUT"]["SELL"]["count"]
        put_buy_amount = cats["PUT"]["BUY"]["amount"]
        put_sell_amount = cats["PUT"]["SELL"]["amount"]

        put_net_count = put_buy_count - put_sell_count
        put_avg1 = put_buy_amount - put_sell_amount
        put_avg2 = put_sell_amount - put_buy_amount
        put_net_avg = put_avg1 - put_avg2
        # put_net_amount = put_buy_amount - put_sell_amount 
        if put_net_count != 0:
            put_avg = put_net_avg / put_net_count
            put_net_amount = put_buy_amount - put_sell_amount
        else:
            put_avg = 0 
            put_net_amount = put_sell_amount - put_buy_amount
    
        strike_prices.append({
            "value": strike,
            "call_total_count": call_net_count,
            "call_avg": (call_net_amount / call_net_count) if call_net_count else 0,
            "call_net_amount": call_net_amount,
            "put_total_count": put_net_count,
            "put_avg": (put_net_amount / put_net_count) if put_net_count else 0,
            "put_net_amount": put_net_amount,
        })
        grand_call_count += call_net_count
        grand_call_amount += call_net_amount
        grand_put_count += put_net_count
        grand_put_amount += put_net_amount
    
    grand_total = {
        "call_total_count": grand_call_count,
        "call_avg": (grand_call_amount/grand_call_count ) if grand_call_count else 0,
        "call_net_amount": grand_call_amount,
        "put_total_count": grand_put_count,
        "put_avg": grand_put_amount/grand_put_count if grand_put_count else 0,
        "put_net_amount": grand_put_amount,
    }

    category_totals = {
        "CALL": {"count": grand_call_count, "avg": grand_total["call_avg"]},
        "PUT":  {"count": grand_put_count, "avg": grand_total["put_avg"]},
    }            

    page_obj = None
    try:
        page_size = request.POST.get('Order_page_size')
        if page_size != '' and page_size != None:
            request.session['Order_page_size'] = page_size
        else:
            page_size = request.session['Order_page_size']
    except:
        page_size = request.session.get('Order_page_size', 50)

    Data=[]
    IPOName = IPO
    products = product
    products = products.select_related("OrderGroup")
    if page_size == 'All':
        all_rows = True
        paginator = Paginator(products,max(len(products), 1))
        page_number = request.GET.get('page','1')
        page_obj = paginator.get_page(page_number)
    else:
        paginator = Paginator(products, page_size)
        page_number = request.GET.get('page','1')
        page_obj = paginator.get_page(page_number)
    

    if products is not None and products.exists():
        start_index = (page_obj.number - 1) * page_obj.paginator.per_page
        for i,order_detail in enumerate(page_obj):
            entry_data = {
                'id':order_detail.id,
                'OrderGroup': order_detail.OrderGroup.GroupName,
                'OrderType': order_detail.OrderType,
                'OrderCategory': order_detail.OrderCategory,
                'InvestorType': order_detail.InvestorType,
                'Quantity': int(order_detail.Quantity) ,
                'Method': order_detail.Method,
                'Rate': order_detail.Rate,
                'Date':order_detail.OrderDate,
                'Time':order_detail.OrderTime,
                'Remark': format_remark(order_detail.remark) or "-",
                'sr_no': start_index + i + 1
            }
            Data.append(entry_data)
        
    df = pd.DataFrame.from_records(Data)
    html_table = "<table class=\"table-bordered sortable\" >"
    html_table = "<thead><tr class='text-center text-nowrap'>"
    html_table += "<th><input type='checkbox' id='select-all-orders' style='cursor:pointer;'> Sr No.</th>"
    html_table += "<th>Group Name</th>"
    html_table += "<th>Order Type</th>"
    html_table += "<th>Order Category</th>"
    html_table += "<th>Premium Strike Price</th>"
    if IPOName.IPOType == "MAINBOARD":
        html_table += "<th>Investor Type</th>"
    html_table += "<th> Qty</th>"
    html_table += "<th>Rate</th>"
    # html_table += "<th>Date and Time</th>"
    # html_table += "<th>Action &nbsp;</th>"
    html_table += "<th class='skip-export'>Date and Time</th>"
    html_table += "<th class='export-only'>Date</th>"
    html_table += "<th class='export-only'>Time</th>"
    html_table += "<th class='remark-col'>Remark</th>"
    html_table += "<th class='skip-export'>Action &nbsp;</th>"
    html_table += "</tr></thead>\n"
    html_table += "<tbody class='text-center text-nowrap'>"
    for i, row in df.iterrows():
        datetime_str  = f"{row.Date} {row.Time}"
        datetime_obj = datetime.strptime(datetime_str , "%Y-%m-%d %H:%M:%S")
        formatted_datetime = datetime_obj.strftime("%b. %d, %Y | %I:%M:%S %p")
    
        # Export formats
        export_date = datetime_obj.strftime("%d-%m-%Y")  # DD-MM-YYYY
        export_time = datetime_obj.strftime("%H:%M:%S")  # HH:MM:SS (24 hr)
    
        html_table += "<tr style='text-align: center;'>"
        html_table += f"<td><input type='checkbox' class='order-checkbox' value='{row.id}' style='cursor:pointer;'> {row.sr_no}</td>"
        html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','{row.OrderGroup}','All','All')\" title=\"Double-click to filter by this Group\">{row.OrderGroup}</td>"
        html_table += f"<td >{row.OrderType}</td>"
        html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','All','{row.OrderCategory}','All')\" title=\"Double-click to filter by this Order Category\">{row.OrderCategory}</td>"
        # if row.InvestorType == 'OPTIONS':
        #     html_table += f"<td>{row.Method}</td>"
        if row.OrderCategory != 'Premium':
            method_value = row.Method if row.Method else 'Application'
            html_table += f"<td>{method_value}</td>"
        else:
            html_table += f"<td>-</td>"
        if IPOName.IPOType == "MAINBOARD":
            html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','All','All','{row.InvestorType}')\" title=\"Double-click to filter by this Investor Type\">{row.InvestorType}</td>"
        if row.OrderCategory != 'Premium' and row.InvestorType != 'OPTIONS':
            html_table += f"<td><a href='/{IPOid}/OrderDetail/{row.OrderType}/{row.OrderGroup}/{ row.OrderCategory }/{row.InvestorType}/{ row.Date.strftime('%Y%m%d') }/{row.Time.strftime('%H%M%S')}{row.id}' style='color:blue; text-decoration: underline; '> {row.Quantity} </a></td>"
        else:
            html_table += f"<td>{row.Quantity}</td>"
        html_table += f"<td>{row.Rate}</td>"
        html_table += f"<td class='skip-export'>{formatted_datetime}</td>"
        html_table += f"<td class='export-only'>{export_date}</td>"
        html_table += f"<td class='export-only'>{export_time}</td>"
        safe_remark = row.Remark.replace("'", "\\'").replace('"', '&quot;') if row.Remark else ""
        html_table += f"<td style='white-space: nowrap; max-width: 300px; overflow: hidden; text-overflow: ellipsis; cursor: pointer; outline: none;' tabindex='0' onclick=\"this.style.whiteSpace=this.style.whiteSpace==='normal'?'nowrap':'normal'\" onblur=\"this.style.whiteSpace='nowrap'\" title='{safe_remark}'>{row.Remark}</td>"
        if IPOName.IPOType == "MAINBOARD":
            url = f'/{IPOid}/EditOrder/{ row.id }/{Groupfilter}/{OrderCategoryFilter}/{InvestorTypeFilter}?page={page_number}'
        else:
            InvestorTypeFilter = 'All'
            url = f'/{IPOid}/EditOrder/{ row.id }/{Groupfilter}/{OrderCategoryFilter}/{InvestorTypeFilter}?page={page_number}'
        html_table += f"<td style='white-space: nowrap;'><button onclick=\"window.location.href='{url}';\"\
                    class='btn btn-outline-primary' style='width: 72px;'>Edit</button></td>"
        html_table += "</tr>\n"
    html_table += "</tbody></table>"

    return render(request, 'Order.html', {'Group': Group.order_by('GroupName'), 'html_table': html_table, 'IPOid': IPOid, 'IPOName': IPO, 'Groupfilter': Groupfilter, 'OrderCategoryFilter': OrderCategoryFilter,'category_totals': category_totals,'strike_prices': strike_prices,'grand_total': grand_total, 'InvestorTypeFilter': InvestorTypeFilter,'PremiumBuyAmount':PremiumBuyAmount,'PremiumNetAmount':PremiumNetAmount,'PremiumSellAmount':PremiumSellAmount ,'dict_count': dict_count, 'net_count':net_count ,'net_avg':net_avg ,'net_amount':net_amount ,'dict_amount':dict_amount,'dict_avg': dict_avg,'PremiumNetCount':PremiumNetCount,'PremiumNetCount':"{:.2f}".format(PremiumNetCount),'PremiumNetAvg':PremiumNetAvg,'PremiumNetAvg':"{:.2f}".format(PremiumNetAvg), 'PremiumBuyCount':PremiumBuyCount,'PremiumSellCount':PremiumSellCount,'PremiumSellAvg':"{:.2f}".format(PremiumSellAvg),'PremiumBuyAvg':"{:.2f}".format(PremiumBuyAvg),'page_obj': page_obj,'Order_page_size':page_size})

def loginUser(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)

        if user is not None:
            Ex_Date  = CustomUser.objects.get( username = user)
            Ex_Date =  Ex_Date.Expiry_Date
            if Ex_Date < now().date():
                messages.error(request, 'Your account has expired. Please contact support.')
                return render(request, 'login.html')
            login(request, user)
            return redirect("/")

        else:
            messages.error(
                request, 'Username or Password is Incorrect')
            return render(request, 'login.html')

    return render(request, 'login.html')

def logoutUser(request):
    logout(request)
    return redirect("/login")


@allowed_users(allowed_roles=['Broker'])
def DeleteAllOrders(request, IPOid):
    """
    DELETES all Orders, OrderDetails, and RateLists for an IPO and 
    AUTOMATICALLY exports the deleted data into a single EXCEL file (.xlsx) 
    containing ONLY the data required for the CSV Re-Upload format.
    """
    user = request.user

    try:
        ipo_name_obj = CurrentIpoName.objects.get(id=IPOid, user=user)
    except CurrentIpoName.DoesNotExist:
        messages.error(request, "IPO not found.")
        return redirect("/")

    # --- 1. FETCH DATA BEFORE DELETION (FOR EXPORT) ---

    # We must fetch ALL Order records because the reupload CSV format corresponds 
    # directly to the Order table structure.
    all_orders_qs = Order.objects.filter(user=user, OrderIPOName_id=IPOid).select_related('OrderGroup')
    order_details_qs = OrderDetail.objects.filter(user=user, Order__OrderIPOName_id=IPOid)

    reupload_data = [] 
    detail_data = []

    # Process all Order records for the 7-column export format
    for o in all_orders_qs:
        # Format date and time for export
        export_date = o.OrderDate.strftime('%d-%m-%Y') if o.OrderDate else ''
        export_time = o.OrderTime.strftime('%H:%M:%S') if o.OrderTime else ''
    
        reupload_data.append([  
            o.OrderGroup.GroupName,
            o.OrderType,
            o.OrderCategory,
            o.InvestorType or 'RETAIL', # Default to RETAIL if null/empty
            o.Quantity,
            o.Rate,
            o.Method or '', # Use Method field for StrikPrice
            export_date,
            export_time
        ])

    for od in order_details_qs:
        pan_no = od.OrderDetailPANNo.PANNo if od.OrderDetailPANNo else ''
        client_name = od.OrderDetailPANNo.Name if od.OrderDetailPANNo else ''
    
        detail_data.append([
            od.Order.OrderGroup.GroupName,
            od.Order.OrderType,
            od.Order.OrderCategory,
            od.Order.InvestorType or 'RETAIL',
            pan_no,
            client_name,
            od.ApplicationNumber or '',
            od.DematNumber or '',
            od.AllotedQty if od.AllotedQty is not None else '',
            od.Order.Rate,
            od.Order.Method or '', # StrikPrice for orders
            od.PreOpenPrice,
            od.Amount,
        ])
    # --- 2. PERFORM DELETION ---
    # Delete related detail records first
    deleted_details_count, _ = order_details_qs.delete()

    # Delete all main Order records
    deleted_orders_count, _ = all_orders_qs.delete()

    # Delete RateList
    RateList.objects.filter(user=user, RateListIPOName_id=IPOid).delete()

    total_orders_deleted = deleted_orders_count

    # --- 3. EXPORT TO SINGLE EXCEL FILE (.xlsx) ---

    # 🟢 Use the requested 7 columns for the DataFrame
    df_reupload = pd.DataFrame(
        reupload_data, 
        columns=['GroupName', 'Ordertype', 'OrderCategory', 'InvestorType', 'Quantity', 'Rate', 'StrikPrice', 'Date', 'Time']
    )
    df_details = pd.DataFrame(
        detail_data,
        columns=[
            'Group Name', 'Order Type', 'Order Category', 'Investor Type', 
            'PAN No', 'Client Name', 'Application Number', 'Demat Number', 
            'Alloted Qty', 'Rate', 'Strike Price/Method', 'Pre-Open Price', 'Amount'
        ]
    )

    # Prepare HttpResponse for Excel download
    file_name = f"Deleted_Orders_Backup_Reupload_{ipo_name_obj.IPOName}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'

    excel_buffer = BytesIO()

    # 🟢 ONLY EXPORT THE 7-COLUMN RE-UPLOAD FORMAT DATA
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        df_reupload.to_excel(writer, sheet_name="1_ReUpload_Orders_Only", index=False)
        # Sheet 2: Application Detail Records (BUY/SELL details)
        df_details.to_excel(writer, sheet_name="2_Application_Details", index=False)

    excel_buffer.seek(0)
    response.write(excel_buffer.read())

    # --- 4. RETURN SUCCESS MESSAGE ---
    messages.success(request, f'Successfully deleted {total_orders_deleted} Orders and {deleted_details_count} OrderDetails. Download of re-upload format Excel file initiated.')

    return response        

# Temporary storage for OTP session
OTP_SESSIONS = {}

@csrf_exempt
def send_telegram_otp(request):
    if request.method == "POST":
        user = request.user
        custom_user = CustomUser.objects.get(username=user)
        # print(f"Custom User: {custom_user}")
        # Validate required fields
        if not custom_user.TelegramApi_id or not custom_user.TelegramApi_key or not custom_user.Mobileno:
            return JsonResponse({
                'status': 'error',
                'message': 'Telegram API ID, API Key, or Mobile number is missing.'
            }, status=400)

        try:
            api_id = int(custom_user.TelegramApi_id)
        except ValueError:
            return JsonResponse({
                'status': 'error',
                'message': 'Telegram API ID must be a valid integer.'
            }, status=400)
        api_hash = custom_user.TelegramApi_key
        phone = custom_user.Mobileno

        async def send_code():
            session = StringSession()
            client = TelegramClient(session, api_id, api_hash)
            await client.connect()
            if not await client.is_user_authorized():
                sent = await client.send_code_request(phone)
                OTP_SESSIONS[user.username] = {
                    "client": client,
                    "session": session,
                    "phone": phone,
                    "api_id": api_id,
                    "api_hash": api_hash,
                    "phone_code_hash": sent.phone_code_hash,
                }
                return {
                    "status": "ok",
                    "message": "OTP sent successfully",
                    "phone": phone,
                    "api_id": api_id,
                    "api_hash": api_hash,
                    "session_string": session.save(),  # Save as string
                    "phone_code_hash": sent.phone_code_hash,
                }
            return {
                "status": "already",
                "message": "User is already authorized"
            }

        try:
            result = asyncio.run(send_code())
            messages.success(request,'Otp sent successfully')
        
            return JsonResponse(result)
        except Exception as e:
            messages.error(request, f'Error sending OTP: {str(e)}')
            return JsonResponse({'status': 'error', 'message': str(e)})

@csrf_exempt
def verify_telegram_otp(request):
    if request.method == "POST":
        user = request.user
        otp = request.POST.get("otp")
        phone = request.POST.get("phone")
        api_id = request.POST.get("api_id")
        api_hash = request.POST.get("api_hash")
        session_string = request.POST.get("session_string")
        phone_code_hash = request.POST.get("phone_code_hash")
    
        # print(f"OTP_SESSIONS: {OTP_SESSIONS}")
        # session_data = OTP_SESSIONS.get(user.username)

        # if not session_data:
        #     return JsonResponse({'status': 'error', 'message': 'No OTP session found'})
        if not all([otp, phone, api_id, api_hash, session_string, phone_code_hash]):
            return JsonResponse({'status': 'error', 'message': 'Missing required data'})

        async def verify_code():
            try:
                # Rebuild the session and client
                client = TelegramClient(StringSession(session_string), int(api_id), api_hash)
                await client.connect()

                if not await client.is_user_authorized():
                    messages.error(request, 'Client is not authorized. Please request OTP again.')
                    await client.sign_in(phone=phone, code=otp, phone_code_hash=phone_code_hash)

                # Save session string to DB
                session_str = client.session.save()
                # custom_user = CustomUser.objects.get(username=user)
                # custom_user.Telegram_session = session_str
                # custom_user.save()
                custom_user = await sync_to_async(CustomUser.objects.get)(username=user)
                custom_user.Telegram_session = session_str
                await sync_to_async(custom_user.save)()

                await client.disconnect()
                messages.success(request, 'Telegram authorized and session saved')
                return {'status': 'success', 'message': 'Telegram authorized and session saved'}
            except Exception as e:
                messages.error(request, f'Error verifying OTP: {str(e)}')
                return {'status': 'error', 'message': str(e)}

        try:
            result = asyncio.run(verify_code())
            messages.success(request, 'Telegram Session Created Successfully')
            return JsonResponse(result)
        except Exception as e:
            messages.error(request, f'Error verifying OTP: {str(e)}')
            return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def user_profile(request):
    user = request.user
    user_detail = CustomUser.objects.get(username = user)
    context = {
        'user': user,
        'user_detail':user_detail,
        'expiry_date': user.Expiry_Date,
    }
    return render(request, 'user_profile.html', context)



@login_required
def update_user_profile(request):
    if request.method == 'POST': 
        user = request.user
        custom_user = CustomUser.objects.get(username=user)

        # Only update fields that are present in the submitted form
        if 'email' in request.POST:
            custom_user.email = request.POST.get('email')

        if 'app_password' in request.POST:
            custom_user.AppPassword = request.POST.get('app_password')

        if 'telegram_api' in request.POST:
            custom_user.TelegramApi_id = request.POST.get('telegram_api')

        if 'telegram_api_key' in request.POST:
            custom_user.TelegramApi_key = request.POST.get('telegram_api_key')

        if 'mobile_number' in request.POST:
            custom_user.Mobileno = request.POST.get('mobile_number')

        custom_user.save()
        # return JsonResponse({"status": "success", "message": "Profile updated successfully!"})
        # print(request.headers)  # Debugging line to check headers
        # print(request.headers.get('x-requested-with'))
        # # ✅ Check if request is AJAX
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            messages.success(request, 'Profile updated successfully!')
            return JsonResponse({"status": "success"})
        else:
            messages.success(request, 'Profile updated successfully!')
            return redirect('user_profile')
        
    messages.error(request, 'Invalid request method.')
    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)


  # in case you need to make paths dynamic

@login_required
@csrf_exempt
def place_order_view(request, IPOid, order_type):
    
    if request.method == "POST":
        form_data = {key: value for key, value in request.POST.items() if key != 'csrfmiddlewaretoken'}
        user = request.user
        
        
        order_type = order_type.upper()
        try:
            custom_user = CustomUser.objects.get(username=user)
        except CustomUser.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User not found'})

        
    
        # Get IPO name
        try:
            ipo_obj = CurrentIpoName.objects.get(id=IPOid, user=user)
            ipo_name = ipo_obj.IPOName
        except CurrentIpoName.DoesNotExist:
            ipo_name = "Unknown IPO"
        # print(f"Placing order for IPO ID: {IPOid}, Type: {order_type}")
        # Get form fields
        group_id = request.POST.get('item_id')
        datetime_val = request.POST.get('datetime')
        premium_qty = request.POST.get('PremiumQTY')
        premium_rate = request.POST.get('PremiumRate')
        # Convert string to datetime object first
        try:
            datetime_obj = datetime.strptime(datetime_val, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            # Try without seconds if the above fails
            datetime_obj = datetime.strptime(datetime_val, "%Y-%m-%dT%H:%M")

        # Now format as you like
        datetime_str = datetime_obj.strftime(" %I:%M:%S %p %d-%m-%Y ")
        
        try:
            group_detail = GroupDetail.objects.get(GroupName=group_id , user=user)
            group_name = group_detail.GroupName
            phone = group_detail.MobileNo
        except GroupDetail.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Please select a valid group with mobile number.'})
        
        # Helper for qty-rate formatting with premium checkbox status
        def format_qty_rate(qty, rate, label_emoji="", label_name="", is_premium=False):
            if qty.strip() or rate.strip():
                premium_indicator = " (Premium Rate)" if is_premium else ""
                return f"{label_emoji} {label_name}: Qty {qty or '—'} @ ₹{rate or '—'}{premium_indicator}"
            return None

        # Build the message lines
        header_lines  = [
            f"**📢 IPO Name: {ipo_name}**",
            f"**📦 Order : {order_type}  From 👥 {group_id}**",
            
            f"**🕒 Date & Time: {datetime_str}**",
            ""
        ]

        lines = []
        # Kostak
        kostak_lines = []
        k_retail = format_qty_rate(request.POST.get('KostakQTY', ''), request.POST.get('KostakRate', ''), " ", "Retail")
        k_shni = format_qty_rate(request.POST.get('KostakQTYSHNI', ''), request.POST.get('KostakRateSHNI', ''), " ", "SHNI")
        k_bhni = format_qty_rate(request.POST.get('KostakQTYBHNI', ''), request.POST.get('KostakRateBHNI', ''), " ", "BHNI")
        for l in (k_retail, k_shni, k_bhni):
            if l: kostak_lines.append(l)
        if kostak_lines:
            lines.append("**🔹 Kostak**")
            # lines.extend(kostak_lines)
            lines.extend([f"  {item}" for item in kostak_lines])
            lines.append("")

        # Subject To - Check premium checkbox status
        subject_lines = []
        # Check if premium checkboxes are checked
        is_premium_retail = request.POST.get('subjectToIsPremiumRetail') == 'on'
        is_premium_shni = request.POST.get('subjectToIsPremiumSHNI') == 'on'
        is_premium_bhni = request.POST.get('subjectToIsPremiumBHNI') == 'on'
        
        s_retail = format_qty_rate(request.POST.get('SubjectToQTY', ''), request.POST.get('SubjectToRate', ''), " ", "Retail", is_premium_retail)
        s_shni = format_qty_rate(request.POST.get('SubjectToQTYSHNI', ''), request.POST.get('SubjectToRateSHNI', ''), " ", "SHNI", is_premium_shni)
        s_bhni = format_qty_rate(request.POST.get('SubjectToQTYBHNI', ''), request.POST.get('SubjectToRateBHNI', ''), " ", "BHNI", is_premium_bhni)
        for l in (s_retail, s_shni, s_bhni):
            if l: subject_lines.append(l)
        if subject_lines:
            lines.append("**🔹 Subject To**")
            # lines.extend(subject_lines)
            lines.extend([f"  {item}" for item in subject_lines])
            
            lines.append("")

        # Premium
        premium_line = None
        if request.POST.get('PremiumQTY', '').strip() or request.POST.get('PremiumRate', '').strip():
            premium_line = f" Qty {request.POST.get('PremiumQTY', '—')} @ ₹{request.POST.get('PremiumRate', '—')}"
        if premium_line:
            lines.append("**🔹 Premium Deal**")
            lines.append(f"    Share:{premium_line}")
            lines.append("")

        # Options
        call_line = None
        if request.POST.get('CallQTY', '').strip() or request.POST.get('CallRate', '').strip():
            call_line = f" Call: Qty {request.POST.get('CallQTY', '—')} | Strike ₹{request.POST.get('CallStrikePrice', '—')} | Rate ₹{request.POST.get('CallRate', '—')}"
        put_line = None
        if request.POST.get('PutQTY', '').strip() or request.POST.get('PutRate', '').strip():
            put_line = f" Put: Qty {request.POST.get('PutQTY', '—')} | Strike ₹{request.POST.get('PutStrikePrice', '—')} | Rate ₹{request.POST.get('PutRate', '—')}"

        if call_line or put_line:
            lines.append("**🔹 Options**")
            if call_line: lines.append(f"    {call_line}")
            if put_line: lines.append(f"    {put_line}")

        if not lines and not custom_user.Telegram_session:
            messages.error(request, f'{order_type} order could not be placed. Telegram session not created. Please set up a Telegram session to send messages.')
            return JsonResponse({'status': 'error', 'message': 'Telegram session not verified yet'})
        
        if not lines:
            # Buy order could not be placed. Please complete all required fields and try again
            messages.error(request, f'{order_type} order could not be placed. Please fill at least one field and try again.')
            return JsonResponse({'status': 'error', 'message': 'No fields entered to send. Please fill at least one field.'})
        
        if not custom_user.Telegram_session:
            messages.warning(request, f'{order_type} order placed successfully. Telegram session not created. Please set up a Telegram session to send messages.')
            return JsonResponse({'status': 'error', 'message': 'Telegram session not verified yet'})
        
        if not phone:
            messages.warning(request, f'{order_type} order placed successfully, but failed to send Telegram message: group mobile number missing.')
            return JsonResponse({
                'status': 'missing_phone',
                'message': 'Order placed successfully, but no group mobile number found. Please add a number to send Telegram message.'
    })

        # Final message
        # message = "\n".join(lines)
        message = "\n".join(header_lines + lines)

        async def send_message():
            async with TelegramClient(
                StringSession(custom_user.Telegram_session),
                int(custom_user.TelegramApi_id),
                custom_user.TelegramApi_key
            ) as client:
                entity = await client.get_entity(f'+91{phone}')
                await client.send_message(entity, message, parse_mode='markdown')

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(asyncio.wait_for(send_message(), timeout=30.0))
            finally:
                loop.close()
            # Sell order placed successfully. Telegram message sent successfully
            success_msg = f" {order_type} order placed successfully. Telegram message sent successfully."
            messages.success(request, success_msg)
            return JsonResponse({'status': 'success', 'message': 'Message sent via Telegram with premium rate information.'})
        except asyncio.TimeoutError:
            messages.error(request, f'{order_type} order placed, but Telegram message timed out (30s).')
            return JsonResponse({'status': 'error', 'message': 'Telegram timeout'})
        except Exception as e:
            # Buy order placed successfully, but failed to send Telegram message: contact not found in group details.
            messages.error(request, f'{order_type} order placed, but failed to send Telegram message: {str(e)}')
            return JsonResponse({'status': 'error', 'message': f'Failed to send Telegram message: {str(e)}'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

# home/views.py


@login_required
@csrf_exempt
def share_status_telegram(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    IPOid = data.get('IPO_id')
    group_names = data.get('group_names', [])
    share_all = data.get('all', False)
    if not IPOid:
        return JsonResponse({'status': 'error', 'message': 'IPO_id required'}, status=400)

    # auth + session
    user = request.user
    try:
        custom_user = CustomUser.objects.get(username=user)
    except CustomUser.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
    if not custom_user.Telegram_session:
        return JsonResponse({'status': 'session_expired', 'message': 'Telegram session not verified yet'}, status=400)

    IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)
    groups_qs = GroupDetail.objects.filter(user=request.user)
    orders = Order.objects.filter(user=request.user, OrderIPOName_id=IPOid)

    # group selection
    if share_all or not group_names:
        groups_to_share = list(
            groups_qs.filter(id__in=orders.values('OrderGroup').distinct())
                     .values_list('GroupName', flat=True)
        )
    else:
        groups_to_share = list(group_names)
    if not groups_to_share:
        return JsonResponse({'status': 'error', 'message': 'No groups to share'}, status=400)

    # helpers
    def sum_qty(qs): return qs.aggregate(total=Sum('Quantity'))['total'] or 0
    def sum_amt(qs): return qs.aggregate(total=Sum('Amount'))['total'] or 0

    # Compute net qty and weighted avg rate like Buy
    def net_qty_and_rate(qs):
        bq = sum_qty(qs.filter(OrderType="BUY"))
        sq = sum_qty(qs.filter(OrderType="SELL"))
        net_q = bq - sq
        amt = sum_amt(qs.filter(OrderType__in=["BUY", "SELL"]))
        rate = round(amt / net_q, 2) if net_q else None
        return net_q, rate

    def line(label, net_q, rate):
        if not (net_q or rate):
            return None
        rt = f"₹{rate:.2f}" if isinstance(rate, (int, float, float)) else "—"
        return f" {label}: Qty {int(net_q) if net_q else 0} @ {rt}"

    payloads, pre = [], []
    now_s = timezone.now().strftime("%Y-%m-%d %H:%M:%S")

    for gname in groups_to_share:
        grp = groups_qs.filter(GroupName=gname).first()
        if not grp or not grp.MobileNo:
            pre.append(f"Failed {gname}: Group/Mobile missing")
            continue

        go = orders.filter(OrderGroup=grp)

        # Kostak (Retail/SHNI/BHNI)
        k_r_q, k_r_r = net_qty_and_rate(go.filter(OrderCategory="Kostak", InvestorType="RETAIL"))
        k_s_q, k_s_r = net_qty_and_rate(go.filter(OrderCategory="Kostak", InvestorType="SHNI"))
        k_b_q, k_b_r = net_qty_and_rate(go.filter(OrderCategory="Kostak", InvestorType="BHNI"))

        # Subject To (Retail/SHNI/BHNI)
        s_r_q, s_r_r = net_qty_and_rate(go.filter(OrderCategory="Subject To", InvestorType="RETAIL"))
        s_s_q, s_s_r = net_qty_and_rate(go.filter(OrderCategory="Subject To", InvestorType="SHNI"))
        s_b_q, s_b_r = net_qty_and_rate(go.filter(OrderCategory="Subject To", InvestorType="BHNI"))

        # Premium (net shares + effective rate)
        p_q, p_r = net_qty_and_rate(go.filter(OrderCategory="Premium"))

        # Options (amounts only)
        call_amt = sum_amt(go.filter(OrderCategory="CALL"))
        put_amt = sum_amt(go.filter(OrderCategory="PUT"))

        # Build Buy-style message
        lines = [
            f"**🆔 Group Name: {gname}**",
            f"**🕒 Date & Time: {now_s}**",
            ""
        ]

        kostak_lines = list(filter(None, [
            line("Retail", k_r_q, k_r_r),
            line("SHNI",   k_s_q, k_s_r),
            line("BHNI",   k_b_q, k_b_r),
        ]))
        if kostak_lines:
            lines.append("**🔹 Kostak**")
            lines.extend(kostak_lines)
            lines.append("")

        subj_lines = list(filter(None, [
            line("Retail", s_r_q, s_r_r),
            line("SHNI",   s_s_q, s_s_r),
            line("BHNI",   s_b_q, s_b_r),
        ]))
        if subj_lines:
            lines.append("**🔹 Subject To**")
            lines.extend(subj_lines)
            lines.append("")

        if p_q or p_r:
            lines.append("**🔹 Premium Deal**")
            rt = f"₹{p_r:.2f}" if isinstance(p_r, (int, float, float)) else "—"
            lines.append(f"Qty {int(p_q) if p_q else 0} @ {rt}")
            lines.append("")

        if call_amt or put_amt:
            lines.append("**🔹 Options**")
            lines.append(f" Call Amt: ₹{call_amt:.1f}")
            lines.append(f" Put Amt: ₹{put_amt:.1f}")

        payloads.append({'name': gname, 'phone': grp.MobileNo, 'message': "\n".join(lines)})

    if not payloads:
        return JsonResponse({'status': 'error', 'message': '; '.join(pre) or 'Nothing to send'}, status=400)

    async def run_send():
        out = pre[:]
        async with TelegramClient(
            StringSession(custom_user.Telegram_session),
            int(custom_user.TelegramApi_id),
            custom_user.TelegramApi_key
        ) as client:
            for p in payloads:
                try:
                    entity = await client.get_entity(f'+91{p["phone"]}')  # adjust prefix if needed
                    await client.send_message(entity, p['message'], parse_mode='markdown')
                    out.append(f"Shared: {p['name']}")
                except Exception as e:
                    out.append(f"Failed {p['name']}: {e}")
        return out

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        sent = loop.run_until_complete(run_send())
        loop.close()
        return JsonResponse({'status': 'success', 'results': sent})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
@csrf_exempt
def send_status_to_telegram(request, IPOid):
    """Send status details to Telegram"""
    if request.method != "POST":
        return JsonResponse({'status': 'error', 'message': 'Only POST method allowed'}, status=405)
    
    try:
        user = request.user
        custom_user = CustomUser.objects.get(username=user)
    except CustomUser.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
    
    if not custom_user.Telegram_session:
        messages.error(request, 'Telegram session not verified yet')
        return JsonResponse({'status': 'session_expired', 'message': 'Telegram session not verified yet'}, status=400)
    
    try:
        IPOName = CurrentIpoName.objects.get(id=IPOid, user=user)
    except CurrentIpoName.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'IPO not found'}, status=404)
    
    # Get all orders for this IPO
    products = Order.objects.filter(user=user, OrderIPOName_id=IPOid)
    
    # Initialize dictionaries for calculations
    dict_count = {}
    dict_avg = {}
    dict_amount = {}
    
    # Define order types and categories
    OrdTyp = ['BUY', 'SELL']
    OrdCat = ['Kostak', 'SubjectTo']
    InvTyp = ['RETAIL', 'SHNI', 'BHNI'] if IPOName.IPOType == "MAINBOARD" else ['RETAIL']
    
    # Calculate counts, averages, and amounts
    for ordertype in OrdTyp:
        for ordercategory in OrdCat:
            for investortype in InvTyp:
                if ordercategory == "SubjectTo":         
                    x = products.filter(OrderType=ordertype, OrderCategory="Subject To", InvestorType=investortype)
                else:
                    x = products.filter(OrderType=ordertype, OrderCategory=ordercategory, InvestorType=investortype)
                
                count = x.aggregate(Sum('Quantity'))['Quantity__sum']
                if count == None:
                    dict_count[f'{ordercategory}{investortype}{ordertype}Count'] = 0
                    z = 0
                else:
                    dict_count[f'{ordercategory}{investortype}{ordertype}Count'] = count
                    z = count

                amount = 0
                for i in x:
                    if i.OrderCategory == 'Subject To':
                        if i.Method == 'Premium':
                            if investortype == 'RETAIL':
                                lot_size = IPOName.LotSizeRetail
                            if investortype == 'SHNI':
                                lot_size = IPOName.LotSizeSHNI
                            if investortype == 'BHNI':
                                lot_size = IPOName.LotSizeBHNI
                            amount = ((lot_size*i.Rate)*i.Quantity) + amount
                        else:
                            amount = i.Rate + amount
                    else:
                        amount = i.Rate + amount
                    
                if z == 0:
                    dict_avg[f'{ordercategory}{investortype}{ordertype}Avg'] = 0
                else:
                    dict_avg[f'{ordercategory}{investortype}{ordertype}Avg'] = amount/z
                
                dict_amount[f'{ordercategory}{investortype}{ordertype}Amount'] = amount
    
    # Calculate net values
    net_count = {}
    net_avg = {}
    net_amount = {}
                
    for ordercategory in OrdCat:
        for investortype in InvTyp:
            # Keys for BUY and SELL
            buy_key_count = f"{ordercategory}{investortype}BUYCount"
            sell_key_count = f"{ordercategory}{investortype}SELLCount"
            
            buy_key_avg = f"{ordercategory}{investortype}BUYAvg"
            sell_key_avg = f"{ordercategory}{investortype}SELLAvg"

            # Get counts (default 0 if missing)
            buy_count = dict_count.get(buy_key_count, 0)
            sell_count = dict_count.get(sell_key_count, 0)
            net_c = buy_count - sell_count

            # Get amounts (Count * Avg)
            buy_amount = buy_count * dict_avg.get(buy_key_avg, 0)
            sell_amount = sell_count * dict_avg.get(sell_key_avg, 0)
            net_amt = buy_amount - sell_amount

            # Calculate net average
            if net_c != 0:
                net_a = net_amt / net_c
            else:
                net_a = 0
                
            if net_c == 0:
                net_amt = sell_amount - buy_amount

            # Store results
            key_prefix = f"{ordercategory}{investortype}Net"
            net_count[f"{key_prefix}Count"] = net_c
            net_avg[f"{key_prefix}Avg"] = round(net_a, 2)
            net_amount[f"{key_prefix}Amount"] = round(net_amt, 2)
    
    # Calculate Premium data
    PremiumBuyfilter = products.filter(OrderType="BUY", OrderCategory="Premium")
    PremiumBuyCount11 = PremiumBuyfilter.aggregate(Sum('Quantity'))
    PremiumBuyCount1 = PremiumBuyCount11['Quantity__sum']
    PremiumBuyCount = PremiumBuyCount1 if PremiumBuyCount1 is not None else 0
    
    PremiumBuyAmount = 0
    for i in PremiumBuyfilter:
        PremiumBuyAmount = (i.Quantity * i.Rate) + PremiumBuyAmount

    PremiumBuyAvg = PremiumBuyAmount / PremiumBuyCount if PremiumBuyCount != 0 else 0
    
    PremiumSellfilter = products.filter(OrderType="SELL", OrderCategory="Premium")
    PremiumSellCount11 = PremiumSellfilter.aggregate(Sum('Quantity'))
    PremiumSellCount1 = PremiumSellCount11['Quantity__sum']
    PremiumSellCount = PremiumSellCount1 if PremiumSellCount1 is not None else 0
    
    PremiumSellAmount = 0
    for i in PremiumSellfilter:
        PremiumSellAmount = (i.Quantity * i.Rate) + PremiumSellAmount

    PremiumSellAvg = PremiumSellAmount / PremiumSellCount if PremiumSellCount != 0 else 0
    
    PremiumNetCount = PremiumBuyCount - PremiumSellCount
    PremiumNetAmount = PremiumBuyAmount - PremiumSellAmount
    PremiumNetAvg = PremiumNetAmount / PremiumNetCount if PremiumNetCount != 0 else 0
    
    # Build Telegram message
    now_str = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    
    lines = [
        f"**📊 {IPOName.IPOName} - Status Report**",
        f"**🕒 Generated: {now_str}**",
        ""
    ]
    
    if IPOName.IPOType == "MAINBOARD":
        # Kostak section for MAINBOARD
        lines.append("**�� Kostak**")
        lines.append("**BUY:**")
        lines.append(f"  Retail: {dict_count.get('KostakRETAILBUYCount', 0):.0f} @ ₹{dict_avg.get('KostakRETAILBUYAvg', 0):.2f} = ₹{dict_amount.get('KostakRETAILBUYAmount', 0):.2f}")
        lines.append(f"  SHNI: {dict_count.get('KostakSHNIBUYCount', 0):.0f} @ ₹{dict_avg.get('KostakSHNIBUYAvg', 0):.2f} = ₹{dict_amount.get('KostakSHNIBUYAmount', 0):.2f}")
        lines.append(f"  BHNI: {dict_count.get('KostakBHNIBUYCount', 0):.0f} @ ₹{dict_avg.get('KostakBHNIBUYAvg', 0):.2f} = ₹{dict_amount.get('KostakBHNIBUYAmount', 0):.2f}")
        lines.append("")
        lines.append("**SELL:**")
        lines.append(f"  Retail: {dict_count.get('KostakRETAILSELLCount', 0):.0f} @ ₹{dict_avg.get('KostakRETAILSELLAvg', 0):.2f} = ₹{dict_amount.get('KostakRETAILSELLAmount', 0):.2f}")
        lines.append(f"  SHNI: {dict_count.get('KostakSHNISELLCount', 0):.0f} @ ₹{dict_avg.get('KostakSHNISELLAvg', 0):.2f} = ₹{dict_amount.get('KostakSHNISELLAmount', 0):.2f}")
        lines.append(f"  BHNI: {dict_count.get('KostakBHNISELLCount', 0):.0f} @ ₹{dict_avg.get('KostakBHNISELLAvg', 0):.2f} = ₹{dict_amount.get('KostakBHNISELLAmount', 0):.2f}")
        lines.append("")
        lines.append("**NET:**")
        lines.append(f"  Retail: {net_count.get('KostakRETAILNetCount', 0):.0f} @ ₹{net_avg.get('KostakRETAILNetAvg', 0):.2f} = ₹{net_amount.get('KostakRETAILNetAmount', 0):.2f}")
        lines.append(f"  SHNI: {net_count.get('KostakSHNINetCount', 0):.0f} @ ₹{net_avg.get('KostakSHNINetAvg', 0):.2f} = ₹{net_amount.get('KostakSHNINetAmount', 0):.2f}")
        lines.append(f"  BHNI: {net_count.get('KostakBHNINetCount', 0):.0f} @ ₹{net_avg.get('KostakBHNINetAvg', 0):.2f} = ₹{net_amount.get('KostakBHNINetAmount', 0):.2f}")
        lines.append("")
        
        # Subject To section for MAINBOARD
        lines.append("**🔹 Subject To**")
        lines.append("**BUY:**")
        lines.append(f"  Retail: {dict_count.get('SubjectToRETAILBUYCount', 0):.0f} @ ₹{dict_avg.get('SubjectToRETAILBUYAvg', 0):.2f} = ₹{dict_amount.get('SubjectToRETAILBUYAmount', 0):.2f}")
        lines.append(f"  SHNI: {dict_count.get('SubjectToSHNIBUYCount', 0):.0f} @ ₹{dict_avg.get('SubjectToSHNIBUYAvg', 0):.2f} = ₹{dict_amount.get('SubjectToSHNIBUYAmount', 0):.2f}")
        lines.append(f"  BHNI: {dict_count.get('SubjectToBHNIBUYCount', 0):.0f} @ ₹{dict_avg.get('SubjectToBHNIBUYAvg', 0):.2f} = ₹{dict_amount.get('SubjectToBHNIBUYAmount', 0):.2f}")
        lines.append("")
        lines.append("**SELL:**")
        lines.append(f"  Retail: {dict_count.get('SubjectToRETAILSELLCount', 0):.0f} @ ₹{dict_avg.get('SubjectToRETAILSELLAvg', 0):.2f} = ₹{dict_amount.get('SubjectToRETAILSELLAmount', 0):.2f}")
        lines.append(f"  SHNI: {dict_count.get('SubjectToSHNISELLCount', 0):.0f} @ ₹{dict_avg.get('SubjectToSHNISELLAvg', 0):.2f} = ₹{dict_amount.get('SubjectToSHNISELLAmount', 0):.2f}")
        lines.append(f"  BHNI: {dict_count.get('SubjectToBHNISELLCount', 0):.0f} @ ₹{dict_avg.get('SubjectToBHNISELLAvg', 0):.2f} = ₹{dict_amount.get('SubjectToBHNISELLAmount', 0):.2f}")
        lines.append("")
        lines.append("**NET:**")
        lines.append(f"  Retail: {net_count.get('SubjectToRETAILNetCount', 0):.0f} @ ₹{net_avg.get('SubjectToRETAILNetAvg', 0):.2f} = ₹{net_amount.get('SubjectToRETAILNetAmount', 0):.2f}")
        lines.append(f"  SHNI: {net_count.get('SubjectToSHNINetCount', 0):.0f} @ ₹{net_avg.get('SubjectToSHNINetAvg', 0):.2f} = ₹{net_amount.get('SubjectToSHNINetAmount', 0):.2f}")
        lines.append(f"  BHNI: {net_count.get('SubjectToBHNINetCount', 0):.0f} @ ₹{net_avg.get('SubjectToBHNINetAvg', 0):.2f} = ₹{net_amount.get('SubjectToBHNINetAmount', 0):.2f}")
        lines.append("")
    else:
        # Kostak section for SME
        lines.append("**�� Kostak**")
        lines.append("**BUY:**")
        lines.append(f"  Count: {dict_count.get('KostakRETAILBUYCount', 0):.0f} @ ₹{dict_avg.get('KostakRETAILBUYAvg', 0):.2f} = ₹{dict_amount.get('KostakRETAILBUYAmount', 0):.2f}")
        lines.append("**SELL:**")
        lines.append(f"  Count: {dict_count.get('KostakRETAILSELLCount', 0):.0f} @ ₹{dict_avg.get('KostakRETAILSELLAvg', 0):.2f} = ₹{dict_amount.get('KostakRETAILSELLAmount', 0):.2f}")
        lines.append("**NET:**")
        lines.append(f"  Count: {net_count.get('KostakRETAILNetCount', 0):.0f} @ ₹{net_avg.get('KostakRETAILNetAvg', 0):.2f} = ₹{net_amount.get('KostakRETAILNetAmount', 0):.2f}")
        lines.append("")
        
        # Subject To section for SME
        lines.append("**🔹 Subject To**")
        lines.append("**BUY:**")
        lines.append(f"  Count: {dict_count.get('SubjectToRETAILBUYCount', 0):.0f} @ ₹{dict_avg.get('SubjectToRETAILBUYAvg', 0):.2f} = ₹{dict_amount.get('SubjectToRETAILBUYAmount', 0):.2f}")
        lines.append("**SELL:**")
        lines.append(f"  Count: {dict_count.get('SubjectToRETAILSELLCount', 0):.0f} @ ₹{dict_avg.get('SubjectToRETAILSELLAvg', 0):.2f} = ₹{dict_amount.get('SubjectToRETAILSELLAmount', 0):.2f}")
        lines.append("**NET:**")
        lines.append(f"  Count: {net_count.get('SubjectToRETAILNetCount', 0):.0f} @ ₹{net_avg.get('SubjectToRETAILNetAvg', 0):.2f} = ₹{net_amount.get('SubjectToRETAILNetAmount', 0):.2f}")
        lines.append("")
    
    # Premium section
    lines.append("**🔹 Premium**")
    lines.append("**BUY:**")
    lines.append(f"  Count: {PremiumBuyCount:.0f} @ ₹{PremiumBuyAvg:.2f} = ₹{PremiumBuyAmount:.2f}")
    lines.append("**SELL:**")
    lines.append(f"  Count: {PremiumSellCount:.0f} @ ₹{PremiumSellAvg:.2f} = ₹{PremiumSellAmount:.2f}")
    lines.append("**NET:**")
    lines.append(f"  Count: {PremiumNetCount:.0f} @ ₹{PremiumNetAvg:.2f} = ₹{PremiumNetAmount:.2f}")
    
    message = "\n".join(lines)
    
    async def send_message():
        try:
            async with TelegramClient(
                StringSession(custom_user.Telegram_session),
                int(custom_user.TelegramApi_id),
                custom_user.TelegramApi_key
            ) as client:
                # Send to saved messages (yourself)
                await client.send_message('me', message, parse_mode='markdown')
                return {'status': 'success', 'message': 'Status sent to Telegram successfully!'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    try:
        result = asyncio.run(send_message())
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)




def generate_status_image(context):
    # context = { 'kostak_data': ..., 'subject_data': ..., etc. }

    html = render_to_string('status_table_template.html', context)

    options = {
        # 'disable-smart-shrinking': '',  # remove this line
        'format': 'png',
        'quality': '100',
        'encoding': "UTF-8",
    }

    # Generate image in memory (not saved to disk)
    # config = imgkit.config(wkhtmltoimage=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltoimage.exe")
    config = imgkit.config(wkhtmltoimage=r"/usr/bin/wkhtmltoimage")  # Adjust path as needed
    
    img_bytes = imgkit.from_string(html, False, options=options,config=config)
    buf = io.BytesIO(img_bytes)
    buf.name = "status_report.png"
    return buf

def get_all_groups(request, IPOid):
    User = request.user
    groups = list(Order.objects.filter(user=User,OrderIPOName=IPOid).values_list('OrderGroup', flat=True).distinct())
    return JsonResponse({'groups': groups})

@login_required
@csrf_exempt
def send_status_to_telegram_image(request, IPOid):
    start_time = time.time()
    if request.method != "POST":
        return JsonResponse({'status': 'error', 'message': 'Only POST method allowed'}, status=405)
    
    try:
        user = request.user
        custom_user = CustomUser.objects.get(username=user)
    except CustomUser.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
    
    if not custom_user.Telegram_session:
        messages.error(request, 'Telegram session not verified yet')
        return JsonResponse({'status': 'session_expired', 'message': 'Telegram session not verified yet'}, status=400)
    
    try:
        IPOName = CurrentIpoName.objects.get(id=IPOid, user=user)
    except CurrentIpoName.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'IPO not found'}, status=404)
    
    if 'image' not in request.FILES:
        messages.error(request, 'No image file provided')
        return JsonResponse({'status': 'error', 'message': 'No image file provided'}, status=400)
    
    image_file = request.FILES['image']
    group_id = request.POST.get('group_id')
    
    if group_id == "null" or group_id == "" or group_id is None or group_id == "All":
        
        batch_group =request.POST.get('batch_group')
        group_ids = [int(g.strip()) for g in batch_group.split(',') if g.strip().isdigit()]
        Groups = GroupDetail.objects.filter(user=user,id__in=group_ids)
        products = Order.objects.filter(
            user=user, OrderIPOName_id=IPOid)
        IPO = IPOName
        
        OrdCat = ['Kostak','SubjectTo','CALL','PUT']
        InvTyp = ['RETAIL','SHNI','BHNI','OPTIONS']
        OrdTyp = ['BUY','SELL']
        
        for group in Groups:
            group_name = group.GroupName
            phone = group.MobileNo
            not_time = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            caption = f"📊 {IPOName.IPOName} - Status Report\n🕒 Generated: {not_time}\n👥 Group: {group_name}"
            strike_dict = {}
            dict_count = {}
            dict_avg = {}
            dict_amount = {}
            products_group = products.filter(OrderGroup=group)
            if not products_group.exists():
                continue        
            if products_group.exists():
                aggregates = (
                    products_group
                    .values("OrderType", "OrderCategory", "InvestorType", "Method")
                    .annotate(
                        total_qty=Sum("Quantity"),
                        total_amt=Sum(F("Rate") * F("Quantity")),
                        total_count=Count("id")
                    )
                ) 
                
                agg_lookup = {}
                for row in aggregates:
                    key = (row["OrderCategory"], row["InvestorType"], row["OrderType"], row["Method"])
                    agg_lookup[key] = {
                        "count": row["total_qty"] or 0,
                        "amount": row["total_amt"] or 0,
                        "entries": row["total_count"] or 0,
                    }  
        
                for ordertype in OrdTyp:
                    for ordercategory in OrdCat:
                        for investortype in InvTyp:
                            key_category = "Subject To" if ordercategory == "SubjectTo" else ordercategory
                            dict_key_prefix = f"{ordercategory}{investortype}{ordertype}"

                            # Lookup (we don’t hit DB here)
                            # NOTE: Method could vary (Premium/Normal/Strike etc.), so we loop over methods in agg_lookup
                            matching_rows = [
                                v for k, v in agg_lookup.items()
                                if k[0] == key_category and k[1] == investortype and k[2] == ordertype
                            ]

                            # Aggregate amounts manually (still in memory, not DB)
                            total_count = sum(v["count"] for v in matching_rows)
                            total_amount = 0

                            for (cat, inv, ot, method), v in agg_lookup.items():
                                if cat == key_category and inv == investortype and ot == ordertype:
                                    # Apply your "Subject To" premium logic here
                                    if cat == "Subject To" and method == "Premium":
                                        if investortype == "RETAIL":
                                            lot_size = IPO.LotSizeRetail
                                        elif investortype == "SHNI":
                                            lot_size = IPO.LotSizeSHNI
                                        elif investortype == "BHNI":
                                            lot_size = IPO.LotSizeBHNI
                                        else:
                                            lot_size = 1
                                        total_amount += (lot_size * v["amount"])
                                    elif investortype == "OPTIONS" and ordercategory in ["CALL", "PUT"]:
                                        
                                        strike = method or "NA"

                                        # Initialize dict structure
                                        if strike not in strike_dict:
                                            strike_dict[strike] = {
                                                "CALL": {"BUY": {"count":0,"amount":0,"avg":0,"net":0},
                                                        "SELL":{"count":0,"amount":0,"avg":0 ,"net":0}},
                                                "PUT":  {"BUY": {"count":0,"amount":0,"avg":0 ,"net":0},
                                                        "SELL":{"count":0,"amount":0,"avg":0 ,"net":0}}
                                            }
                                        # Update values
                                        # strike_dict[strike][ordercategory][ordertype]["count"] += v.Quantity
                                        # strike_dict[strike][ordercategory][ordertype]["amount"] += (v.Rate * v.Quantity)
                                        strike_dict[strike][ordercategory][ordertype]["count"] += v["count"]
                                        strike_dict[strike][ordercategory][ordertype]["amount"] += v["amount"]

                                        # Calculate average
                                        c = strike_dict[strike][ordercategory][ordertype]["count"]
                                        a = strike_dict[strike][ordercategory][ordertype]["amount"]
                                        strike_dict[strike][ordercategory][ordertype]["avg"] = (a / c) if c else 0
                                        
                                        # Net = (BUY amount - SELL amount) for that side
                                        buy_amt  = strike_dict[strike][ordercategory]["BUY"]["amount"]
                                        sell_amt = strike_dict[strike][ordercategory]["SELL"]["amount"]
                                        strike_dict[strike][ordercategory]["BUY"]["net"]  = buy_amt - sell_amt
                                        strike_dict[strike][ordercategory]["SELL"]["net"] = sell_amt - buy_amt
                                        
                                        # amount = (v.Rate * v.Quantity) + amount
                                        total_amount += v["amount"]
                                    else:
                                        total_amount += v["amount"]

                            # Save into dicts
                            dict_count[f"{dict_key_prefix}Count"] = total_count
                            dict_avg[f"{dict_key_prefix}Avg"] = (total_amount / total_count) if total_count else 0
                            dict_amount[f"{dict_key_prefix}Amount"] = total_amount
                        
                net_count = {}
                net_avg = {}
                net_amount = {}
                            
                for ordercategory in OrdCat:
                    for investortype in InvTyp:
                        # Keys for BUY and SELL
                        buy_key_count = f"{ordercategory}{investortype}BUYCount"
                        sell_key_count = f"{ordercategory}{investortype}SELLCount"
                        
                        buy_key_avg = f"{ordercategory}{investortype}BUYAvg"
                        sell_key_avg = f"{ordercategory}{investortype}SELLAvg"

                        # Get counts (default 0 if missing)
                        buy_count = dict_count.get(buy_key_count, 0)
                        sell_count = dict_count.get(sell_key_count, 0)
                        net_c = buy_count - sell_count

                        # Get amounts (Count * Avg)
                        buy_amount = buy_count * dict_avg.get(buy_key_avg, 0)
                        sell_amount = sell_count * dict_avg.get(sell_key_avg, 0)
                        net_amt = buy_amount - sell_amount

                        # Calculate net average
                        if net_c != 0:
                            net_a = net_amt / net_c
                        else:
                            net_a = 0
                            
                        if net_c == 0:
                            net_amt = sell_amount - buy_amount

                        # Store results
                        key_prefix = f"{ordercategory}{investortype}Net"
                        net_count[f"{key_prefix}Count"] = net_c
                        net_avg[f"{key_prefix}Avg"] = round(net_a, 2)
                        net_amount[f"{key_prefix}Amount"] = round(net_amt, 2)   
                        # Calculate Premium data    

                PremiumBuyfilter = products_group.filter(OrderType="BUY",OrderCategory="Premium")
                # PremiumBuyCount11 = PremiumBuyfilter.aggregate(Sum('Quantity'))
                matching_rows = [
                    v for k, v in agg_lookup.items()
                    if k[0] == "Premium" and k[1] == "PREMIUM" and k[2] == "BUY"
                ]
                PremiumBuyCount1 = sum(v["count"] for v in matching_rows)
                if PremiumBuyCount1 == None:
                    PremiumBuyCount = 0
                else:
                    PremiumBuyCount = PremiumBuyCount1
                
                PremiumBuyAmount=0
                for i in PremiumBuyfilter:
                    PremiumBuyAmount=(i.Quantity*i.Rate)+PremiumBuyAmount

                if PremiumBuyCount==0:
                    PremiumBuyAvg=0    
                else:
                    PremiumBuyAvg=PremiumBuyAmount/PremiumBuyCount
                
                PremiumSellfilter = products_group.filter(OrderType="SELL",OrderCategory="Premium")
                # PremiumSellCount11 = PremiumSellfilter.aggregate(Sum('Quantity'))
                matching_rows = [
                    v for k, v in agg_lookup.items()
                    if k[0] == "Premium" and k[1] == "PREMIUM" and k[2] == "SELL"
                ]
                PremiumSellCount1 = sum(v["count"] for v in matching_rows)
                if PremiumSellCount1 == None:
                    PremiumSellCount = 0
                else:
                    PremiumSellCount = PremiumSellCount1

                PremiumSellAmount=0
                for i in PremiumSellfilter:
                    PremiumSellAmount=(i.Quantity*i.Rate)+PremiumSellAmount

                if PremiumSellCount==0:
                    PremiumSellAvg=0    
                else:
                    PremiumSellAvg=PremiumSellAmount/PremiumSellCount

                PremiumNetCount = PremiumBuyCount - PremiumSellCount
                Premiumavg1 = PremiumBuyCount * PremiumBuyAvg
                Premiumavg2 = PremiumSellCount * PremiumSellAvg
                pri_net_avg = Premiumavg1 - Premiumavg2
                if PremiumNetCount != 0:
                    PremiumNetAvg = pri_net_avg /PremiumNetCount
                    PremiumNetAmount = PremiumBuyAmount - PremiumSellAmount
                else:
                    PremiumNetAvg =  0
                    PremiumNetAmount = PremiumSellAmount - PremiumBuyAmount
                    
                strike_prices = []
                grand_call_count = grand_call_amount = grand_put_count = grand_put_amount = 0
                for strike, cats in strike_dict.items():
                    # CALL
                    call_buy_count = cats["CALL"]["BUY"]["count"]
                    call_sell_count = cats["CALL"]["SELL"]["count"]
                    call_buy_amount = cats["CALL"]["BUY"]["amount"]
                    call_sell_amount = cats["CALL"]["SELL"]["amount"]

                    
                    call_net_count = call_buy_count - call_sell_count
                    call_avg1 = call_buy_amount - call_sell_amount
                    call_avg2 = call_sell_amount - call_buy_amount
                    call_net_avg = call_avg1 - call_avg2
                    # call_net_amount = call_buy_amount - call_sell_amount
                    if call_net_count != 0:
                        call_avg = call_net_avg / call_net_count
                        call_net_amount = call_buy_amount - call_sell_amount
                    else:
                        call_avg = 0
                        call_net_amount = call_sell_amount - call_buy_amount
                    
                    # PUT
                    put_buy_count = cats["PUT"]["BUY"]["count"]
                    put_sell_count = cats["PUT"]["SELL"]["count"]
                    put_buy_amount = cats["PUT"]["BUY"]["amount"]
                    put_sell_amount = cats["PUT"]["SELL"]["amount"]

                    put_net_count = put_buy_count - put_sell_count
                    put_avg1 = put_buy_amount - put_sell_amount
                    put_avg2 = put_sell_amount - put_buy_amount
                    put_net_avg = put_avg1 - put_avg2
                    # put_net_amount = put_buy_amount - put_sell_amount 
                    if put_net_count != 0:
                        put_avg = put_net_avg / put_net_count
                        put_net_amount = put_buy_amount - put_sell_amount
                    else:
                        put_avg = 0 
                        put_net_amount = put_sell_amount - put_buy_amount
                    
                    strike_prices.append({
                        "value": strike,
                        "call_total_count": call_net_count,
                        "call_avg": (call_net_amount / call_net_count) if call_net_count else 0,
                        "call_net_amount": call_net_amount,
                        "put_total_count": put_net_count,
                        "put_avg": (put_net_amount / put_net_count) if put_net_count else 0,
                        "put_net_amount": put_net_amount,
                    })
                    grand_call_count += call_net_count
                    grand_call_amount += call_net_amount
                    grand_put_count += put_net_count
                    grand_put_amount += put_net_amount
                    
                grand_total = {
                    "call_total_count": grand_call_count,
                    "call_avg": (grand_call_amount/grand_call_count ) if grand_call_count else 0,
                    "call_net_amount": grand_call_amount,
                    "put_total_count": grand_put_count,
                    "put_avg": grand_put_amount/grand_put_count if grand_put_count else 0,
                    "put_net_amount": grand_put_amount,
                }
                
                category_totals = {
                    "CALL": {"count": grand_call_count, "avg": grand_total["call_avg"]},
                    "PUT":  {"count": grand_put_count, "avg": grand_total["put_avg"]},
                }
                
                context ={
                    'strike_prices': strike_prices,
                    'grand_total': grand_total, 
                    'PremiumBuyAmount':PremiumBuyAmount,
                    'PremiumNetAmount':PremiumNetAmount,
                    'PremiumSellAmount':PremiumSellAmount ,
                    'dict_count': dict_count, 
                    'net_count':net_count ,
                    'net_avg':net_avg ,
                    'net_amount':net_amount ,
                    'dict_amount':dict_amount,
                    'dict_avg': dict_avg,
                    'PremiumNetCount':PremiumNetCount,
                    'PremiumNetCount':"{:.2f}".format(PremiumNetCount),
                    'PremiumNetAvg':PremiumNetAvg,
                    'PremiumNetAvg':"{:.2f}".format(PremiumNetAvg), 
                    'PremiumBuyCount':PremiumBuyCount,
                    'PremiumSellCount':PremiumSellCount,
                    'PremiumSellAvg':"{:.2f}".format(PremiumSellAvg),
                    'PremiumBuyAvg':"{:.2f}".format(PremiumBuyAvg)
                }
                
                combined_img = generate_status_image(context)
                
                async def send_image(image_buf):
                    client = TelegramClient(
                        StringSession(custom_user.Telegram_session),
                        int(custom_user.TelegramApi_id),
                        custom_user.TelegramApi_key
                    )
                    await client.start()

                    try:
                        entity = await client.get_entity(f'+91{phone}')
                        await client.send_file(
                            entity,
                            file=image_buf,  # <- Use BytesIO buffer, not file path
                            caption=caption,
                            parse_mode='markdown'
                        )
                        # return {'status': 'success', 'message': f'Status image sent to Telegram successfully for group {group_name}!'}
                        print(f"Image sent to group {group_name} successfully.")
                    except Exception as e:
                        pass
                        # return {'status': 'error', 'message': f'Error sending to group {group_name}: {str(e)}'}
                    finally:
                        await client.disconnect()
                try:
                    # asyncio.run(send_image(kostak_img))
                    # asyncio.run(send_image(subject_img))
                    asyncio.run(send_image(combined_img))
                    messages.success(request, f'Status image sent to Telegram successfully for group {group_name}!')
                except Exception as e:
                    messages.error(request, f'Error sending to group {group_name}: {str(e)}')
                    # return JsonResponse({'status': 'partial_success', 'message': 'Status image sent to some groups, but errors occurred for others.'})
                    continue
        
        return JsonResponse({'status': 'success', 'message': 'Status image sent to Telegram successfully!'})
                                   
    else:
        if not group_id:
            messages.error(request, 'Group ID is required')
            return JsonResponse({'status': 'error', 'message': 'Group ID is required'}, status=400)

        try:
            group_detail = GroupDetail.objects.get(GroupName=group_id , user=request.user)
            group_name = group_detail.GroupName
            phone = group_detail.MobileNo
        except (GroupDetail.DoesNotExist, ValueError):
            messages.error(request, 'Please select a valid group with mobile number')
            return JsonResponse({'status': 'error', 'message': 'Selected group not found'}, status=404)
        now_str = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        caption = f"📊 {IPOName.IPOName} - Status Report\n🕒 Generated: {now_str}\n👥 Group: {group_name}"
    
        async def send_image():
            client = TelegramClient(
                StringSession(custom_user.Telegram_session),
                int(custom_user.TelegramApi_id),
                custom_user.TelegramApi_key
            )
            await client.start()

            entity = await client.get_entity(f'+91{phone}')
            await client.send_file(
                entity,
                image_file,
                caption=caption,
                parse_mode='markdown'
            )

            await client.disconnect()
        
        try:
            asyncio.run(send_image())
            messages.success(request, 'Status image sent to Telegram successfully!')
            
            return JsonResponse({'status': 'success', 'message': 'Status image sent to Telegram successfully!'})


        except Exception as e:
            messages.error(request, f' Please enter a mobile number for the {group_name} group .' );
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def accounting_view(request):
    show_all = request.GET.get("show_all")
    show_deleted = request.GET.get("show_deleted", "0") == "1"
    entries = Accounting.objects.filter(user=request.user).select_related("group", "ipo")
    
    # Filter by soft-delete status
    if show_deleted:
        entries = entries.filter(is_deleted=True)
    else:
        entries = entries.filter(is_deleted=False)

    IPO_DropDown = []
    for entry in entries:
        name = entry.ipo_name
        if name and name not in IPO_DropDown:
            IPO_DropDown.append(name)
    
    Group_DropDown = []
    for entry in entries:
        gname =  entry.group_name
        if gname and gname not in Group_DropDown:
            Group_DropDown.append(gname)
    
    Group_DropDown.sort()
        # if entry.ipo_id:  # FK exists
        #     IPO_DropDown.append(entry.ipo.IPOName)  # from related IPO table
        # else:
        #     IPO_DropDown.append(entry.ipo_name or "")  # from local field
    
    # group_id = request.GET.get("group_id")
    # ipo_id = request.GET.get("ipo_id")
    group_name = request.GET.get("group_name")  # string instead of group_id
    ipo_name = request.GET.get("ipo_name")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    
    # if ipo_name:
    #     ipo_name = unquote(ipo_name)
    #     entries = entries.filter(Q(ipo__IPOName__iexact=ipo_name) | Q(ipo_name__iexact=ipo_name))
    #     print("Filtered entries count after ipo_name:", entries.count())
    # --- filter by ipo_name string ---
    if ipo_name:
        ipo_name = unquote(ipo_name)

        if ipo_name == "JV":
            # User explicitly selected "JV"
            entries = entries.filter(jv=True)
            # print("Filtered entries for JV only:", entries.count())
        else:
            entries = entries.filter(Q(ipo__IPOName__iexact=ipo_name) | Q(ipo_name__iexact=ipo_name))
            # print("Filtered entries count after ipo_name:", entries.count())


    # --- filter by group_name string ---
    if group_name:
        group_name = unquote(group_name)
        entries = entries.filter(Q(group__GroupName__iexact=group_name) | Q(group_name__iexact=group_name))
        # print("Filtered entries count after group_name:", entries.count())
    # --- filter by dates ---
    if date_from:
        # date_from_obj = datetime.fromisoformat(date_from) + timedelta(days=1) - timedelta(seconds=1)
        date_from_obj = datetime.fromisoformat(date_from).date()  # extract date only
        # print("date_from_obj", date_from_obj)
        entries = entries.filter(date_time__gte=date_from_obj)
        # print("Filtered entries count after date_from:", entries.count())

    if date_to:
        date_to_obj = datetime.fromisoformat(date_to) + timedelta(days=1) - timedelta(seconds=1)
        # print("date_to_obj", date_to_obj)
        entries = entries.filter(date_time__lte=date_to_obj)
        # print("Filtered entries count after date_to:", entries.count())
     
    
    jv_filter = request.GET.get('jv')
    if jv_filter == '1':
        entries = entries.filter(jv=True)
    elif jv_filter == '0':
        entries = entries.filter(jv=False)
        
    order_by = request.GET.get("order_by")
    # default to 'desc' so newest first
    order_dir = request.GET.get("order_dir", "desc")

    if order_by:
        if order_by == "ipo":
            sort_field = "ipo__IPOName"
        elif order_by == "group":
            sort_field = "group__GroupName"
        else:
            sort_field = order_by
        if order_dir == "desc":
            sort_field = f"-{sort_field}"
        entries = entries.order_by(sort_field)
    else:
        # Default sort when no explicit column is requested:
        # newest first by date_time, then by id
        entries = entries.order_by("-date_time", "-id")
    
    # Calculate total credit, debit, and net per group (JV=True)
    jv_sums = Accounting.objects.filter(
        user=request.user,
        jv=True,
        is_deleted=False,
    ).values('group__GroupName').annotate(
        total_credit=Sum(Case(When(amount_type='credit', then=F('amount')), default=0, output_field=FloatField())),
        total_debit=Sum(Case(When(amount_type='debit', then=F('amount')), default=0, output_field=FloatField())),
        net=Sum(Case(
            When(amount_type='credit', then=F('amount')),
            When(amount_type='debit', then=-F('amount')),
            output_field=FloatField()
        ))
    )
    jv_sum_dict = {item['group__GroupName']: item for item in jv_sums}
    ipo_name = request.GET.get("ipo_name")
    

    # # Check in database
    # if e.ipo:
    #     ipo_display = e.ipo.IPOName
    # elif ipo_obj:
    #     ipo_display = ipo_obj.ipo.IPOName if ipo_obj.ipo else ipo_obj.ipo_name
    # else:
    #     ipo_display = ''

    rows = ""
    credit_amount = 0
    debit_amount = 0
    displayed_batches = set()
    for e in entries:
        if e.amount_type == 'credit' :
            credit_amount = credit_amount + e.amount
        else:
            debit_amount = debit_amount + e.amount

        if e.transfer_batch_id:
            if e.transfer_batch_id in displayed_batches:
                continue
            displayed_batches.add(e.transfer_batch_id)

            batch_entries = list(Accounting.objects.filter(
                user=request.user,
                transfer_batch_id=e.transfer_batch_id,
                is_deleted=show_deleted,
            ).select_related("group", "ipo").order_by("id"))
            if not batch_entries:
                continue

            credit_total = sum(
                (item.amount for item in batch_entries if item.amount_type == "credit"),
                Decimal("0.00"),
            )
            debit_total = sum(
                (item.amount for item in batch_entries if item.amount_type == "debit"),
                Decimal("0.00"),
            )
            transfer_amount = max(credit_total, debit_total)
            group_names = list(dict.fromkeys(
                item.group.GroupName if item.group else (item.group_name or "Deleted")
                for item in batch_entries
            ))
            group_display = " → ".join(group_names)
            batch_key = str(e.transfer_batch_id)
            batch_user_remark = ""
            first_batch_remark = batch_entries[0].remark or ""
            if len(group_names) > 1:
                summary_prefixes = (
                    f"Transfer to {group_names[1]}",
                    f"Transfer excess to {group_names[1]}",
                )
                for prefix in summary_prefixes:
                    if first_batch_remark.startswith(prefix):
                        batch_user_remark = first_batch_remark[len(prefix):]
                        if batch_user_remark.startswith(" - "):
                            batch_user_remark = batch_user_remark[3:]
                        break
            detail_rows = ""
            for item in batch_entries:
                item_ipo = item.ipo.IPOName if item.ipo else "JV"
                item_group = item.group.GroupName if item.group else (item.group_name or "Deleted")
                item_date = timezone.localtime(item.date_time)
                detail_style = (
                    "opacity: 0.6; background-color: #ffe6e6;"
                    if show_deleted else "background-color: #f8f9fa;"
                )
                detail_rows += f"""
                <tr class="bulk-transfer-detail-row" data-transfer-batch="{batch_key}" style="display:none; {detail_style}">
                    <td class="filter-ipo" data-ipo="{escape(item_ipo)}">↳ {escape(item_ipo)}</td>
                    <td class="filter-group" data-group="{escape(item_group)}">{escape(item_group)}</td>
                    <td><span class="badge {'bg-success' if item.amount_type == 'credit' else 'bg-danger'}">{escape(item.amount_type.upper())}</span></td>
                    <td>{item.amount}</td>
                    <td><textarea class="form-control form-control-sm" readonly>{escape(item.remark or '')}</textarea></td>
                    <td data-order="{item_date.strftime('%Y-%m-%d %H:%M:%S')}">{item_date.strftime('%d-%m-%y %H:%M:%S')}</td>
                    <td class="no-export"></td>
                </tr>
                """
            batch_date = batch_entries[0].date_time
            representative_id = batch_entries[0].id
            batch_action = (
                f"<button type='button' disabled='true' class='btn btn-sm btn-outline-success restore-btn' "
                f"data-id='{representative_id}' title='Restore this bulk transfer'>"
                "<i class='fas fa-undo'></i> Restore</button>"
                if show_deleted else
                f"<button type='button' class='btn btn-sm btn-outline-primary bulk-transfer-edit-btn' "
                f"data-transfer-batch='{batch_key}' title='Edit this bulk transfer'>"
                "<i class='fas fa-edit'></i></button> "
                f"<button type='button' class='btn btn-sm btn-outline-danger delete-btn' "
                f"data-id='{representative_id}' title='Delete this bulk transfer'>"
                "<i class='fas fa-trash'></i></button>"
            )
            rows += f"""
            <tr class="bulk-transfer-row" data-transfer-batch="{batch_key}" style="{'opacity: 0.6; background-color: #ffe6e6;' if show_deleted else ''}">
                <td><strong>Bulk Transfer</strong></td>
                <td>{escape(group_display)}</td>
                <td><span class="badge bg-primary">TRANSFER</span></td>
                <td>{transfer_amount}</td>
                <td>
                    {f'<div style="white-space: normal; margin-bottom: 6px;" title="{escape(batch_user_remark)}">{escape(batch_user_remark)}</div>' if batch_user_remark else ''}
                    <button type="button" class="btn btn-sm btn-outline-secondary bulk-transfer-toggle"
                            data-transfer-batch="{batch_key}" aria-expanded="false">
                        View {len(batch_entries)} entries
                    </button>
                </td>
                <td data-order="{timezone.localtime(batch_date).strftime('%Y-%m-%d %H:%M:%S')}">
                    {timezone.localtime(batch_date).strftime("%d-%m-%y %H:%M:%S")}
                </td>
                <td class="no-export">{batch_action}</td>
            </tr>
            {detail_rows}
            """
            continue

         # Priority 1: Use IPO from entry
        if e.ipo:  # If FK exists
            ipo_display = e.ipo.IPOName
        elif e.ipo_name:  # Fallback to stored field
            ipo_display = f"{e.ipo_name} (Deleted)" 
        else:
            ipo_display = "JV"
        if e.group:  # FK exists
            group_name1 = e.group.GroupName
        else:
            group_name1 = f"{e.group_name}(Deleted)" or ""
        group_jv_total = jv_sum_dict.get(group_name1, 0)  # Only sum for jv=True
        # Prepare attributes for edit button
        ipo_id_val = e.ipo.id if e.ipo else ""
        group_id_val = e.group.id if e.group else ""
        dt_local = timezone.localtime(e.date_time).strftime("%Y-%m-%dT%H:%M:%S")
        safe_remark = escape(e.remark or "")
        
        rows += f"""
        <tr style="{'opacity: 0.6; background-color: #ffe6e6;' if show_deleted else ''}">
            <td class="filter-ipo" data-ipo="{ipo_display}">{ipo_display}</td>
            <td class="filter-group" data-group="{group_name1}">{group_name1}</td>
            <td><span class="badge {'bg-success' if e.amount_type=='credit' else 'bg-danger'}">{e.amount_type.upper()}</span></td>
            <td>{e.amount}</td>
            <td><textarea class="form-control form-control-sm" readonly>{e.remark or ''}</textarea></td>
            
            <td data-order="{timezone.localtime(e.date_time).strftime('%Y-%m-%d %H:%M:%S')}">
                {timezone.localtime(e.date_time).strftime("%d-%m-%y %H:%M:%S")}
            </td>
            <td class="no-export">
                {f'''<button type="button" disabled='true' class="btn btn-sm btn-outline-success restore-btn" data-id="{e.id}" title="Restore this entry"><i class="fas fa-undo"></i> Restore</button>''' if show_deleted else f'''<button type="button" class="btn btn-sm btn-outline-primary edit-btn" 
                        data-id="{e.id}" 
                        data-ipo-id="{ipo_id_val}" 
                        data-group-id="{group_id_val}" 
                        data-amount="{e.amount}" 
                        data-amount-type="{e.amount_type}" 
                        data-jv="{'1' if e.jv else '0'}"
                        data-remark="{safe_remark}" 
                        data-datetime="{dt_local}">
                    <i class="fas fa-edit"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-danger delete-btn ms-1" data-id="{e.id}" title="Delete this entry">
                    <i class="fas fa-trash"></i>
                </button>'''}
            </td>
        </tr>
        """
        
    net_amount = credit_amount - debit_amount
    html_table = "<table >\n"
    html_table = "<thead><tr style='text-align: center;white-space: nowrap; width:100%' >"
    html_table += "<th>IPO</th>"
    html_table += "<th>Group</th>"
    html_table += "<th>Amount Type</th>"
    html_table += "<th>Amount</th>"
    html_table += "<th>Remark</th>"
    html_table += "<th>Date Time</th>"
    html_table += "<th class='no-export'>Action</th>"
    html_table += "</tr></thead>\n"
    html_table += f"<tbody style='text-align: center;white-space: nowrap;'> {rows} </tbody>\n"
    html_table += "</table>"
            
    ipos_master = CurrentIpoName.objects.filter(user=request.user)
    groups_master = GroupDetail.objects.filter(user=request.user).order_by('GroupName')

    return render(request, "accounting.html", {
        "entries": entries,
        "html_table": format_html(html_table),
        "ipos": IPO_DropDown,
        "groups": Group_DropDown,
        "ipos1": ipos_master,
        "groups1": groups_master, 
        "selected_group": group_name,
        "selected_ipo": ipo_name,
        "date_from": date_from,
        "date_to": date_to,
        "debit_amount":debit_amount,
        "credit_amount":credit_amount,
        "Net_amount" : net_amount,
        "order_by": order_by or "date_time",
        "order_dir": order_dir or "desc",
        "show_deleted": show_deleted,
    })

@login_required
def accounting_logs_view(request):
    audit_logs = list(
        AccountingAuditLog.objects.filter(user=request.user)
        .select_related('accounting__group', 'accounting__ipo')
        .order_by('-timestamp')[:500]
    )
    audit_log_html = ""
    if audit_logs:
        audit_log_html = "<table id='auditLogTable' class='table table-bordered table-sm table-hover'>\n"
        audit_log_html += "<thead><tr>"
        audit_log_html += "<th>Timestamp</th>"
        audit_log_html += "<th>Transaction</th>"
        audit_log_html += "<th>Action</th>"
        audit_log_html += "<th>Details</th>"
        audit_log_html += "</tr></thead>\n"
        audit_log_html += "<tbody>"
        shown_bulk_actions = set()
        displayed_rows = 0
        for log in audit_logs:
            if displayed_rows >= 100:
                break

            # Action badge
            if log.action == 'EDIT':
                badge = "<span class='badge bg-warning text-dark'>Edited</span>"
            elif log.action == 'SOFT_DELETE':
                badge = "<span class='badge bg-danger'>Deleted</span>"
            elif log.action == 'RESTORE':
                badge = "<span class='badge bg-success'>Restored</span>"
            else:
                badge = f"<span class='badge bg-secondary'>{escape(log.action)}</span>"
            
            acc = log.accounting
            if acc.transfer_batch_id:
                operation_key = (
                    str(acc.transfer_batch_id),
                    log.action,
                    timezone.localtime(log.timestamp).replace(microsecond=0),
                )
                if operation_key in shown_bulk_actions:
                    continue
                shown_bulk_actions.add(operation_key)

                operation_logs = [
                    item for item in audit_logs
                    if item.accounting.transfer_batch_id == acc.transfer_batch_id
                    and item.action == log.action
                    and timezone.localtime(item.timestamp).replace(microsecond=0) == operation_key[2]
                ]
                operation_entries = sorted(
                    {item.accounting_id: item.accounting for item in operation_logs}.values(),
                    key=lambda item: item.id,
                )
                group_names = list(dict.fromkeys(
                    item.group.GroupName if item.group else (item.group_name or 'Deleted group')
                    for item in operation_entries
                ))
                direction = " → ".join(group_names) if group_names else "Group transfer"
                credit_total = sum(
                    (item.amount for item in operation_entries if item.amount_type == 'credit'),
                    Decimal('0.00'),
                )
                debit_total = sum(
                    (item.amount for item in operation_entries if item.amount_type == 'debit'),
                    Decimal('0.00'),
                )
                transfer_amount = max(credit_total, debit_total)
                reference = min(item.id for item in operation_entries)
                ts = timezone.localtime(log.timestamp).strftime("%d-%m-%Y %H:%M:%S")
                details = (
                    f"<div><b>From → To:</b> {escape(direction)}</div>"
                    f"<div><b>Amount:</b> ₹{transfer_amount:.2f}</div>"
                    f"<div><b>Entries:</b> {len(operation_entries)}</div>"
                )
                audit_log_html += (
                    f"<tr class='bulk-audit-row'><td>{ts}</td>"
                    f"<td><b>Bulk Transfer #{reference}</b></td>"
                    f"<td>{badge}</td><td>{details}</td></tr>\n"
                )
                displayed_rows += 1
                continue

            # Transaction ref
            ipo_ref = acc.ipo.IPOName if acc.ipo else (acc.ipo_name or 'JV')
            grp_ref = acc.group.GroupName if acc.group else (acc.group_name or '')
            txn_ref = f"{ipo_ref} / {grp_ref}" if grp_ref else ipo_ref
            
            # Changes summary
            changes = log.changes or {}
            changes_parts = []
            for field, vals in changes.items():
                if isinstance(vals, dict) and 'old' in vals and 'new' in vals:
                    if field == 'Amount Type':
                        def style_amt(amt):
                            amt_str = str(amt).lower()
                            if amt_str == 'debit':
                                return f"<span class='badge rounded-pill bg-danger'>{escape(amt)}</span>"
                            elif amt_str == 'credit':
                                return f"<span class='badge rounded-pill bg-success'>{escape(amt)}</span>"
                            return escape(amt)
                        changes_parts.append(f"<b>{field}:</b> {style_amt(vals['old'])} → {style_amt(vals['new'])}")
                    else:
                        changes_parts.append(f"<b>{escape(field)}:</b> {escape(vals['old'])} → {escape(vals['new'])}")
                elif field == 'note':
                    changes_parts.append(f"<i>{escape(vals)}</i>")
                else:
                    changes_parts.append(f"<b>{escape(field)}:</b> {escape(vals)}")
            changes_str = "<br>".join(changes_parts) if changes_parts else "-"
            
            ts = timezone.localtime(log.timestamp).strftime("%d-%m-%Y %H:%M:%S")
            audit_log_html += f"<tr><td>{ts}</td><td>{escape(txn_ref)}</td><td>{badge}</td><td>{changes_str}</td></tr>\n"
            displayed_rows += 1
        audit_log_html += "</tbody></table>"

    return render(request, "accounting_logs.html", {
        "audit_log_html": format_html(audit_log_html),
    })



def get_accounting_entries(request):
    try:
        group_id = request.GET.get("group_id")
        ipo_id = request.GET.get("ipo_id")
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")

        entries = Accounting.objects.filter(user=request.user).order_by("-date_time")

        if group_id:
            entries = entries.filter(group_id=group_id)
        if ipo_id:
            entries = entries.filter(ipo_id=ipo_id)
        if date_from and date_to:
            entries = entries.filter(date_time__date__range=[date_from, date_to])
        
        # Include ipo_id and group_id for JS
        entries_data = [{
            "ipo": entry.ipo.IPOName if entry.ipo else "N/A",
            "ipo_id": entry.ipo.id if entry.ipo else None,
            "group": entry.group.GroupName if entry.group else "N/A",
            "group_id": entry.group.id if entry.group else None,
            "amount_type": entry.amount_type.lower(),
            "amount": str(entry.amount),
            "remark": entry.remark or "",
            "jv": "Yes" if entry.jv else "No",
            "date_time": entry.date_time.strftime("%Y-%m-%d %H:%M:%S")
        } for entry in entries]

        return JsonResponse({
            "data": entries_data,
            "ipos": [{"id": ipo.id, "name": ipo.IPOName} for ipo in CurrentIpoName.objects.filter(user=request.user)],
            "groups": [{"id": g.id, "name": g.GroupName} for g in GroupDetail.objects.filter(user=request.user)],
        })
    except Exception as e:
        messages.error(request, f' Error fetching accounting entries .' );
        return JsonResponse({"error": str(e)}, status=500)

@login_required
def delete_accounting_entries(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            entry_ids = data.get('entry_ids', [])
            
            if not entry_ids:
                return JsonResponse({'status': 'error', 'message': 'No entries selected for deletion'}, status=400)
            
            # Delete the entries
            deleted_count = Accounting.objects.filter(
                id__in=entry_ids,
                user=request.user  # Ensure user can only delete their own entries
            ).delete()[0]
            
            if deleted_count > 0:
                return JsonResponse({
                    'status': 'success', 
                    'message': f'Successfully deleted {deleted_count} entries'
                })
            else:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'No entries found or you do not have permission to delete them'
                }, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            print(f"Error deleting accounting entries: {e}")
            
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)



def ipo_transaction(request):
    if request.method == "POST":
        user = request.user
        
       
        ipo_id_left = request.POST.get("ipo_id_left") or None
        group_id_left = request.POST.get("group_id_left") or None
        amount_left = float(request.POST.get("amount_left") or request.POST.get("amount") or 0)
        amount_type_left = request.POST.get("amount_type_left") or request.POST.get("amount_type")
        remark_left = request.POST.get("remark_left") or ""
        date_time_left = request.POST.get("date_time_left")
        date_time_left = parse_datetime(date_time_left) if date_time_left else timezone.now()
        
        ipo_id_right = request.POST.get("ipo_id_right") or None
        group_id_right = request.POST.get("group_id_right") or None
        amount_right = float(request.POST.get("amount_right") or amount_left)
        amount_type_right = request.POST.get("amount_type_right") or ("debit" if amount_type_left == "credit" else "credit")
        remark_right = request.POST.get("remark_right") or ""
        date_time_right = request.POST.get("date_time_right")
        date_time_right = parse_datetime(date_time_right) if date_time_right else timezone.now()
        
        # --- GET RELATED NAMES FOR DEFAULT REMARKS ---
        # left_group_name = Group.objects.filter(id=group_id_left).values_list("name", flat=True).first() or ""
        # right_group_name = Group.objects.filter(id=group_id_right).values_list("name", flat=True).first() or ""
        # left_ipo_name = CurrentIpoName.objects.filter(id=ipo_id_left).values_list("IPOName", flat=True).first() or ""
        # right_ipo_name = CurrentIpoName.objects.filter(id=ipo_id_right).values_list("IPOName", flat=True).first() or ""

        
        # # --- DEFAULT REMARK LOGIC (same as JS) ---
        # if not remark_left:
        #     if amount_type_left == "credit":
        #         remark_left = f"Given to {right_group_name} for {right_ipo_name}"
        #     elif amount_type_left == "debit":
        #         remark_left = f"Received from {right_group_name} for {right_ipo_name}"

        # if not remark_right:
        #     if amount_type_left == "credit":
        #         remark_right = f"Received from {left_group_name} for {left_ipo_name}"
        #     elif amount_type_left == "debit":
        #         remark_right = f"Given to {left_group_name} for {left_ipo_name}"
        
        try:
            
            Accounting.objects.create(
                user=user,
                ipo_id=int(ipo_id_left) if ipo_id_left else None,
                group_id=int(group_id_left) if group_id_left else None,
                amount=amount_left,
                amount_type=amount_type_left,
                remark=remark_left[:250],
                date_time=date_time_left,
                jv=0
            )

            
            Accounting.objects.create(
                user=user,
                ipo_id=int(ipo_id_right) if ipo_id_right else None,
                group_id=int(group_id_right) if group_id_right else None,
                amount=amount_right,
                amount_type=amount_type_right,
                remark=remark_right[:250],
                date_time=date_time_right,
                jv=0
            )

            return redirect("accounting")

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "error", "message": "Invalid request"})

def ipo_transaction1(request):
    if request.method == "POST":
        user = request.user
        
        ipo_id_left = request.POST.get("ipo_id_left") or None
        group_id_left = request.POST.get("group_id_left") or None
        amount_left = float(request.POST.get("amount_left") or request.POST.get("amount") or 0)
        amount_type_left = request.POST.get("amount_type_left") or request.POST.get("amount_type")
        remark_left = request.POST.get("remark_left") or ""
        date_time_left = request.POST.get("date_time_left")
        date_time_left = parse_datetime(date_time_left) if date_time_left else timezone.now()
        
        ipo_id_right = request.POST.get("ipo_id_right") or None
        group_id_right = request.POST.get("group_id_right") or None
        amount_right = float(request.POST.get("amount_right") or amount_left)
        amount_type_right = request.POST.get("amount_type_right") or ("debit" if amount_type_left == "credit" else "credit")
        remark_right = request.POST.get("remark_right") or ""
        date_time_right = request.POST.get("date_time_right")
        date_time_right = parse_datetime(date_time_right) if date_time_right else timezone.now()
        
        try:
            
            Accounting.objects.create(
                user=user,
                ipo_id=int(ipo_id_left) if ipo_id_left else None,
                group_id=int(group_id_left) if group_id_left else None,
                amount=amount_left,
                amount_type=amount_type_left,
                remark=remark_left[:250],
                date_time=date_time_left,
                jv=0
            )

            
            Accounting.objects.create(
                user=user,
                ipo_id=int(ipo_id_right) if ipo_id_right else None,
                group_id=int(group_id_right) if group_id_right else None,
                amount=amount_right,
                amount_type=amount_type_right,
                remark=remark_right[:250],
                date_time=date_time_right,
                jv=0
            )

            return redirect("GroupWiseDashboard")

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "error", "message": "Invalid request"})


def save_transaction(request):
    if request.method == "POST":
        user = request.user
        ipo_id = request.POST.get("ipo_id")
        group_id = request.POST.get("group_id")
        amount_type = request.POST.get("amount_type")
        amount = request.POST.get("amount")
        remark = request.POST.get("remark")or ""
        date_time = request.POST.get("date_time")
        date_time = parse_datetime(date_time) if date_time else timezone.now()
        
        jv_group_id = request.POST.get("jv_group_id")
        # jv_remark: $('#jv_remark').val(),
        jv_remark1 = request.POST.get("jv_remark")
        
                
        # Get IPO and Group names
        ipo_obj = CurrentIpoName.objects.filter(id=ipo_id).first()
        group_obj = GroupDetail.objects.filter(id=group_id).first()
        ipo_name = ipo_obj.IPOName if ipo_obj else f"IPO ID {ipo_id}"
        group_name = group_obj.GroupName if group_obj else f"Group ID {group_id}"
        
        # default_remark = f"JV from {group_name} for {ipo_name}"
        # jv_remark1 = f"{default_remark}  {jv_remark}" 
        
        
        try:
            # Non-JV entry
            first_entry = Accounting.objects.create(
                user=user,
                ipo_id=ipo_id,
                group_id=group_id,
                amount=amount,
                amount_type=amount_type,
                remark=remark,
                date_time=date_time,
                jv=0
            )

            # JV entry
            # Second entry (opposite - JV=1)
            opposite_type = "debit" if amount_type == "credit" else "credit"
            
            second_entry = Accounting.objects.create(
                user=user,
                ipo_id=None,
                group_id=jv_group_id,
                amount=amount,
                amount_type=opposite_type,
                remark=jv_remark1,
                date_time=date_time,
                jv=1
            )

            return redirect("accounting")  
            # return JsonResponse({"status": "success"})

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "error", "message": "Invalid request"})

def save_transaction_group(request):
    if request.method == "POST":
        user = request.user
        ipo_id = request.POST.get("ipo_id")
        group_id = request.POST.get("group_id")
        amount_type = request.POST.get("amount_type")
        amount = request.POST.get("amount")
        remark = request.POST.get("remark")or ""
        date_time = request.POST.get("date_time")
        date_time = parse_datetime(date_time) if date_time else timezone.now()
        
        jv_group_id = request.POST.get("jv_group_id")
        # jv_remark: $('#jv_remark').val(),
        jv_remark1 = request.POST.get("jv_remark")
        
                
        # Get IPO and Group names
        ipo_obj = CurrentIpoName.objects.filter(id=ipo_id).first()
        group_obj = GroupDetail.objects.filter(id=group_id).first()
        ipo_name = ipo_obj.IPOName if ipo_obj else f"IPO ID {ipo_id}"
        group_name = group_obj.GroupName if group_obj else f"Group ID {group_id}"
        
        # default_remark = f"JV from {group_name} for {ipo_name}"
        # jv_remark1 = f"{default_remark}  {jv_remark}" 
        
        
        try:
            # Non-JV entry
            first_entry = Accounting.objects.create(
                user=user,
                ipo_id=ipo_id,
                group_id=group_id,
                amount=amount,
                amount_type=amount_type,
                remark=remark,
                date_time=date_time,
                jv=0
            )

            # JV entry
            # Second entry (opposite - JV=1)
            opposite_type = "debit" if amount_type == "credit" else "credit"
            
            second_entry = Accounting.objects.create(
                user=user,
                ipo_id=None,
                group_id=jv_group_id,
                amount=amount,
                amount_type=opposite_type,
                remark=jv_remark1,
                date_time=date_time,
                jv=1
            )

            return redirect("GroupWiseDashboard")  
            # return JsonResponse({"status": "success"})

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "error", "message": "Invalid request"})


@login_required
def update_accounting(request):
    if request.method == "POST":
        try:
            entry_id = request.POST.get("entry_id")
            entry = get_object_or_404(Accounting, id=entry_id, user=request.user)
            if entry.transfer_batch_id:
                raise ValidationError(
                    "Use the Bulk Transfer edit button to edit this entry."
                )

            group = _get_owned_group(request.user, request.POST.get("group_id"))
            ipo_id = request.POST.get("ipo_id")
            ipo = None
            if entry.jv:
                ipo_id = None
            else:
                if not ipo_id:
                    raise ValidationError("A valid IPO is required.")
                ipo = _get_owned_ipo(request.user, ipo_id)

            amount_type = request.POST.get("amount_type")
            if amount_type not in VALID_TRANSACTION_TYPES:
                raise ValidationError("Invalid amount type.")
            amount = _parse_transaction_amount(request.POST.get("amount"))
            remark = _validate_transaction_remark(request.POST.get("remark"))
            date_time = _parse_transaction_datetime(request.POST.get("date_time"))
            if ipo is not None:
                _validate_ipo_payment(
                    request.user,
                    group,
                    ipo,
                    amount,
                    amount_type,
                    exclude_entry_id=entry.id,
                )
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
            return redirect("accounting")

        # Save original values for JV finding and audit log
        orig_amount = entry.amount
        orig_amount_type = entry.amount_type
        orig_date_time = entry.date_time
        orig_ipo_id = entry.ipo_id
        orig_group_id = entry.group_id
        orig_remark = entry.remark or ""

        # Build changes dict for audit log
        changes = {}
        new_ipo_id = ipo.id if ipo else None
        new_group_id = group.id
        new_amount = amount

        if orig_ipo_id != new_ipo_id:
            old_ipo_name = entry.ipo.IPOName if entry.ipo else str(orig_ipo_id or "None")
            new_ipo_obj = ipo
            new_ipo_name = new_ipo_obj.IPOName if new_ipo_obj else str(new_ipo_id or "None")
            changes["IPO"] = {"old": old_ipo_name, "new": new_ipo_name}

        if orig_group_id != new_group_id:
            old_group_name = entry.group.GroupName if entry.group else str(orig_group_id or "None")
            new_group_obj = group
            new_group_name = new_group_obj.GroupName if new_group_obj else str(new_group_id or "None")
            changes["Group"] = {"old": old_group_name, "new": new_group_name}

        if orig_amount != new_amount:
            changes["Amount"] = {"old": str(orig_amount), "new": str(new_amount)}

        if orig_amount_type != amount_type:
            changes["Amount Type"] = {"old": orig_amount_type, "new": amount_type}

        if orig_remark != remark:
            changes["Remark"] = {"old": orig_remark, "new": remark}

        if orig_date_time != date_time:
            changes["Date/Time"] = {
                "old": timezone.localtime(orig_date_time).strftime("%d-%m-%Y %H:%M:%S") if orig_date_time else "",
                "new": timezone.localtime(date_time).strftime("%d-%m-%Y %H:%M:%S") if date_time else ""
            }

        # Log audit entry if any changes detected
        if changes:
            AccountingAuditLog.objects.create(
                user=request.user,
                accounting=entry,
                action='EDIT',
                changes=changes
            )

        # Update current entry
        entry.ipo = ipo
        entry.group = group
        entry.amount = amount
        entry.amount_type = amount_type
        entry.remark = remark
        entry.date_time = date_time
        entry.save()

        # Update JV sibling if exists
        siblings = Accounting.objects.filter(
            user=request.user,
            date_time=orig_date_time,
            amount=orig_amount,
            jv=not entry.jv,
            is_deleted=False,
            transfer_batch_id__isnull=True,
        ).exclude(id=entry.id)
        
        if siblings.exists() and siblings.count() == 1:
            sibling = siblings.first()
            if sibling.amount_type != orig_amount_type:
                sibling_changes = {}
                if orig_amount != new_amount:
                    sibling_changes["Amount"] = {"old": str(orig_amount), "new": str(new_amount)}
                if orig_amount_type != amount_type:
                    old_sib_amt_type = sibling.amount_type
                    new_sib_amt_type = "debit" if amount_type == "credit" else "credit"
                    sibling_changes["Amount Type"] = {"old": old_sib_amt_type, "new": new_sib_amt_type}
                if orig_date_time != date_time:
                    sibling_changes["Date/Time"] = {
                        "old": timezone.localtime(orig_date_time).strftime("%d-%m-%Y %H:%M:%S") if orig_date_time else "",
                        "new": timezone.localtime(date_time).strftime("%d-%m-%Y %H:%M:%S") if date_time else ""
                    }
                
                sibling.amount = amount
                sibling.amount_type = "debit" if amount_type == "credit" else "credit"
                sibling.date_time = date_time
                sibling.save()

                if sibling_changes:
                    sibling_group = sibling.group.GroupName if sibling.group else (sibling.group_name or "")
                    sibling_changes["note"] = f"JV sibling [ {sibling_group} ] auto-edited"
                    AccountingAuditLog.objects.create(
                        user=request.user,
                        accounting=sibling,
                        action='EDIT',
                        changes=sibling_changes
                    )

        return redirect("accounting")

    return JsonResponse({"status": "error", "message": "Invalid request"})


@login_required
@csrf_exempt
def soft_delete_accounting(request, entry_id):
    if request.method == "POST":
        entry = get_object_or_404(Accounting, id=entry_id, user=request.user)

        if entry.transfer_batch_id:
            batch_entries = Accounting.objects.filter(
                user=request.user,
                transfer_batch_id=entry.transfer_batch_id,
                is_deleted=False,
            )
            deleted_at = timezone.now()
            with transaction.atomic():
                for batch_entry in batch_entries:
                    batch_entry.is_deleted = True
                    batch_entry.deleted_at = deleted_at
                    batch_entry.save(update_fields=["is_deleted", "deleted_at"])
                    AccountingAuditLog.objects.create(
                        user=request.user,
                        accounting=batch_entry,
                        action="SOFT_DELETE",
                        changes={"note": f"Bulk transfer {entry.transfer_batch_id} deleted"},
                    )
            return JsonResponse({"success": True})
        
        # Soft delete the entry
        entry.is_deleted = True
        entry.deleted_at = timezone.now()
        entry.save()

        # Log audit
        AccountingAuditLog.objects.create(
            user=request.user,
            accounting=entry,
            action='SOFT_DELETE',
            changes={
                "IPO": entry.ipo.IPOName if entry.ipo else (entry.ipo_name or ""),
                "Group": entry.group.GroupName if entry.group else (entry.group_name or ""),
                "Amount": str(entry.amount),
                "Amount Type": entry.amount_type,
            }
        )

        # Also soft-delete JV sibling if exists
        siblings = Accounting.objects.filter(
            user=request.user,
            date_time=entry.date_time,
            amount=entry.amount,
            is_deleted=False
        ).exclude(id=entry.id)
        
        if siblings.exists() and siblings.count() == 1:
            sibling = siblings.first()
            if sibling.amount_type != entry.amount_type:
                sibling.is_deleted = True
                sibling.deleted_at = timezone.now()
                sibling.save()
                sibling_group = sibling.group.GroupName if sibling.group else (sibling.group_name or "")
                AccountingAuditLog.objects.create(
                    user=request.user,
                    accounting=sibling,
                    action='SOFT_DELETE',
                    changes={"note": f"JV sibling [ {sibling_group} ] auto-deleted"}
                )

        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "error": "Invalid request"})


@login_required
@csrf_exempt
def restore_accounting(request, entry_id):
    if request.method == "POST":
        entry = get_object_or_404(Accounting, id=entry_id, user=request.user)

        if entry.transfer_batch_id:
            batch_entries = Accounting.objects.filter(
                user=request.user,
                transfer_batch_id=entry.transfer_batch_id,
                is_deleted=True,
            )
            with transaction.atomic():
                for batch_entry in batch_entries:
                    batch_entry.is_deleted = False
                    batch_entry.deleted_at = None
                    batch_entry.save(update_fields=["is_deleted", "deleted_at"])
                    AccountingAuditLog.objects.create(
                        user=request.user,
                        accounting=batch_entry,
                        action="RESTORE",
                        changes={"note": f"Bulk transfer {entry.transfer_batch_id} restored"},
                    )
            return JsonResponse({"success": True})
        
        # Restore the entry
        entry.is_deleted = False
        entry.deleted_at = None
        entry.save()

        # Log audit
        AccountingAuditLog.objects.create(
            user=request.user,
            accounting=entry,
            action='RESTORE',
            changes={
                "IPO": entry.ipo.IPOName if entry.ipo else (entry.ipo_name or ""),
                "Group": entry.group.GroupName if entry.group else (entry.group_name or ""),
                "Amount": str(entry.amount),
                "Amount Type": entry.amount_type,
            }
        )

        # Also restore JV sibling if exists
        siblings = Accounting.objects.filter(
            user=request.user,
            date_time=entry.date_time,
            amount=entry.amount,
            is_deleted=True
        ).exclude(id=entry.id)
        
        if siblings.exists() and siblings.count() == 1:
            sibling = siblings.first()
            if sibling.amount_type != entry.amount_type:
                sibling.is_deleted = False
                sibling.deleted_at = None
                sibling.save()
                sibling_group = sibling.group.GroupName if sibling.group else (sibling.group_name or "")
                AccountingAuditLog.objects.create(
                    user=request.user,
                    accounting=sibling,
                    action='RESTORE',
                    changes={"note": f"JV sibling [ {sibling_group} ] auto-restored"}
                )

        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "error": "Invalid request"})


VALID_TRANSACTION_TYPES = {"credit", "debit"}
MONEY_QUANTUM = Decimal("0.01")


def _parse_transaction_amount(value):
    try:
        amount = Decimal(str(value)).quantize(MONEY_QUANTUM)
    except (decimal.InvalidOperation, TypeError, ValueError):
        raise ValidationError("Invalid amount.")
    if not amount.is_finite() or amount <= 0:
        raise ValidationError("Amount must be greater than zero.")
    if amount > Decimal("9999999999.99"):
        raise ValidationError("Amount is too large.")
    return amount


def _parse_transaction_datetime(value):
    if not value:
        raise ValidationError("Date and time is required.")
    try:
        parsed = parse_datetime(value)
    except (TypeError, ValueError):
        parsed = None
    if parsed is None:
        raise ValidationError("Invalid date and time.")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    if parsed.year < 2020 or parsed.year > 2035:
        raise ValidationError("Date and time must be between 2020 and 2035.")
    return parsed


def _get_owned_group(user, group_id):
    try:
        group = GroupDetail.objects.filter(id=group_id, user=user).first()
    except (TypeError, ValueError):
        group = None
    if group is None:
        raise ValidationError("Invalid group.")
    return group


def _get_owned_ipo(user, ipo_id):
    try:
        ipo = CurrentIpoName.objects.filter(id=ipo_id, user=user).first()
    except (TypeError, ValueError):
        ipo = None
    if ipo is None:
        raise ValidationError("Invalid IPO.")
    return ipo


def _validate_transaction_remark(value):
    remark = str(value or "").strip()
    if len(remark) > 250:
        raise ValidationError("Remark cannot exceed 250 characters.")
    return remark


def _get_group_ipo_outstanding(user, group, ipo, exclude_entry_id=None):
    order_total = Order.objects.filter(
        user=user,
        OrderGroup=group,
        OrderIPOName=ipo,
    ).aggregate(total=Sum("Amount"))["total"] or Decimal("0.00")
    accounting_query = Accounting.objects.filter(
        user=user,
        group=group,
        ipo=ipo,
        is_deleted=False,
    )
    if exclude_entry_id is not None:
        accounting_query = accounting_query.exclude(id=exclude_entry_id)
    accounting_total = accounting_query.aggregate(
        total=Sum(Case(
            When(amount_type="credit", then=F("amount")),
            When(amount_type="debit", then=-F("amount")),
            output_field=DecimalField(),
        ))
    )["total"] or Decimal("0.00")
    return (
        Decimal(str(order_total)) - Decimal(str(accounting_total))
    ).quantize(MONEY_QUANTUM)


def _validate_ipo_payment(
    user, group, ipo, amount, amount_type, exclude_entry_id=None
):
    outstanding = _get_group_ipo_outstanding(
        user, group, ipo, exclude_entry_id=exclude_entry_id
    )
    if outstanding == Decimal("0.00"):
        raise ValidationError(
            f"{ipo.IPOName} has no outstanding balance for {group.GroupName}."
        )
    required_type = "debit" if outstanding < 0 else "credit"
    if amount_type != required_type:
        raise ValidationError(
            f"{ipo.IPOName} requires a {required_type.title()} payment."
        )
    if amount > abs(outstanding):
        raise ValidationError(
            f"{ipo.IPOName} payment cannot exceed its outstanding balance of ₹{abs(outstanding):.2f}."
        )
    return outstanding


def _create_single_transaction(request, redirect_name):
    if request.method != "POST":
        return redirect(redirect_name)

    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    try:
        group = _get_owned_group(request.user, request.POST.get("group_id"))
        is_jv = request.POST.get("jv") == "1"
        ipo = None
        if not is_jv:
            ipo_id = request.POST.get("ipo_id")
            if not ipo_id or ipo_id == "all":
                raise ValidationError("A valid IPO is required.")
            ipo = _get_owned_ipo(request.user, ipo_id)

        amount_type = request.POST.get("amount_type")
        if amount_type not in VALID_TRANSACTION_TYPES:
            raise ValidationError("Invalid amount type.")

        amount = _parse_transaction_amount(request.POST.get("amount"))
        if ipo is not None:
            _validate_ipo_payment(request.user, group, ipo, amount, amount_type)

        Accounting.objects.create(
            user=request.user,
            ipo=ipo,
            group=group,
            amount_type=amount_type,
            amount=amount,
            remark=_validate_transaction_remark(request.POST.get("remark")),
            date_time=_parse_transaction_datetime(request.POST.get("date_time")),
            jv=is_jv,
        )
    except ValidationError as exc:
        if is_ajax:
            return JsonResponse(
                {"status": "error", "message": exc.messages[0]}, status=400
            )
        messages.error(request, exc.messages[0])
        return redirect(redirect_name)

    if is_ajax:
        return JsonResponse(
            {"status": "success", "message": "Payment saved successfully."}
        )
    return redirect(redirect_name)


@login_required
def add_transaction(request):
    if request.method == "POST":
        return _create_single_transaction(request, "accounting")

    # if GET request → render form
    from .models import IPO, Group
    
    ipos = IPO.objects.filter(user=request.user)
    groups = Group.objects.filter(user=request.user)
    return render(request, "accounting/Accounting.html", {"ipos": ipos, "groups": groups, "now":timezone.localtime()})

@login_required
def add_transaction_group(request):
    if request.method == "POST":
        return _create_single_transaction(request, "GroupWiseDashboard")

    # if GET request → render form
    from .models import IPO, Group
    
    ipos = IPO.objects.filter(user=request.user)
    groups = Group.objects.filter(user=request.user)
    return render(request, "GroupWiseDashboard.html", {"ipos": ipos, "groups": groups, "now":timezone.localtime()})

@login_required
def bulk_ipo_transactions(request):
    """Handle bulk IPO transactions for multiple IPO entries from Total column"""
    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "POST required"}, status=405
        )

    try:
        items = json.loads(request.POST.get("transactions", "[]"))
        if not isinstance(items, list) or not items:
            raise ValidationError("At least one transaction is required.")
        if len(items) > 500:
            raise ValidationError("Too many transactions.")

        master_amount = _parse_transaction_amount(request.POST.get("master_amount"))
        master_type = request.POST.get("master_amount_type")
        if master_type not in VALID_TRANSACTION_TYPES:
            raise ValidationError("Invalid master amount type.")
        expected_total = master_amount if master_type == "credit" else -master_amount

        records = []
        signed_total = Decimal("0.00")
        gross_total = Decimal("0.00")
        submitted_group_id = None
        submitted_date = None
        seen_ipo_ids = set()
        jv_count = 0
        for item in items:
            if not isinstance(item, dict):
                raise ValidationError("Invalid transaction entry.")

            group = _get_owned_group(request.user, item.get("group_id"))
            if submitted_group_id is None:
                submitted_group_id = group.id
            elif group.id != submitted_group_id:
                raise ValidationError("All allocations must use the same group.")

            is_jv = item.get("jv") in (1, True, "1")
            ipo = None
            if is_jv:
                jv_count += 1
                if jv_count > 1:
                    raise ValidationError("Only one JV allocation is allowed.")
            else:
                ipo_id = item.get("ipo_id")
                if not ipo_id:
                    raise ValidationError("An IPO is required for non-JV entries.")
                ipo = _get_owned_ipo(request.user, ipo_id)
                if ipo.id in seen_ipo_ids:
                    raise ValidationError("Duplicate IPO allocation is not allowed.")
                seen_ipo_ids.add(ipo.id)

            amount_type = item.get("amount_type")
            if amount_type not in VALID_TRANSACTION_TYPES:
                raise ValidationError("Invalid amount type.")
            amount = _parse_transaction_amount(item.get("amount"))
            if amount_type != master_type:
                raise ValidationError("Every allocation must use the selected amount type.")
            if ipo is not None:
                _validate_ipo_payment(request.user, group, ipo, amount, amount_type)
            gross_total += amount
            signed_total += amount if amount_type == "credit" else -amount
            item_date = _parse_transaction_datetime(item.get("date_time"))
            if submitted_date is None:
                submitted_date = item_date
            elif item_date != submitted_date:
                raise ValidationError("All allocations must use the same date and time.")

            records.append(Accounting(
                user=request.user,
                ipo=ipo,
                group=group,
                amount=amount,
                amount_type=amount_type,
                remark=_validate_transaction_remark(item.get("remark")),
                date_time=item_date,
                jv=is_jv,
            ))

        if gross_total > master_amount:
            raise ValidationError("Allocated amount exceeds the payment amount.")
        if signed_total.quantize(MONEY_QUANTUM) != expected_total:
            raise ValidationError("Allocation total does not match the payment amount.")

        with transaction.atomic():
            Accounting.objects.bulk_create(records)

        created_count = len(records)
        messages.success(request, f'Successfully created {created_count} IPO-wise transactions.')
        return JsonResponse({
            "status": "success",
            "message": f"Successfully created {created_count} IPO-wise transactions",
        })
    except json.JSONDecodeError:
        return JsonResponse(
            {"status": "error", "message": "Invalid transaction data."}, status=400
        )
    except ValidationError as exc:
        return JsonResponse(
            {"status": "error", "message": exc.messages[0]}, status=400
        )
    except Exception as exc:
        traceback.print_exc()
        message = str(exc) if settings.DEBUG else "Server error while saving payment."
        return JsonResponse({"status": "error", "message": message}, status=500)
@login_required
def bulk_transfer_transactions(request):
    """Create a balanced multi-IPO transfer without changing legacy handlers."""
    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "POST required"}, status=405
        )

    try:
        payload = json.loads(request.body or b"{}")
        if not isinstance(payload, dict):
            raise ValidationError("Invalid transfer data.")

        mode = payload.get("mode")
        if mode != "ipo":
            raise ValidationError("Only IPO to IPO transfers are supported.")

        edit_batch_id = None
        existing_batch = Accounting.objects.none()
        if payload.get("transfer_batch_id"):
            try:
                edit_batch_id = uuid.UUID(str(payload.get("transfer_batch_id")))
            except (ValueError, TypeError, AttributeError):
                raise ValidationError("Invalid transfer batch.")
            existing_batch = Accounting.objects.filter(
                user=request.user,
                transfer_batch_id=edit_batch_id,
                is_deleted=False,
            )
            if not existing_batch.exists():
                raise ValidationError("Transfer batch was not found.")

        source_type = payload.get("source_type")
        if source_type not in VALID_TRANSACTION_TYPES:
            raise ValidationError("Invalid source amount type.")
        destination_type = "debit" if source_type == "credit" else "credit"

        master_amount = _parse_transaction_amount(payload.get("master_amount"))
        source_group = _get_owned_group(
            request.user, payload.get("source_group_id")
        )
        destination_group = _get_owned_group(
            request.user, payload.get("destination_group_id")
        )
        if source_group.id == destination_group.id:
            raise ValidationError("Source and destination groups must be different.")
        transfer_date = _parse_transaction_datetime(payload.get("date_time"))
        user_remark = str(payload.get("remark") or "").strip()[:250]

        def validate_allocations(items, side, expected_type):
            if not isinstance(items, list):
                raise ValidationError(f"Invalid {side} allocations.")
            if len(items) > 100:
                raise ValidationError(f"Too many {side} IPOs selected.")

            validated = []
            seen_ids = set()
            signed_total = Decimal("0.00")
            gross_total = Decimal("0.00")
            for item in items:
                if not isinstance(item, dict):
                    raise ValidationError(f"Invalid {side} allocation.")
                ipo = _get_owned_ipo(request.user, item.get("ipo_id"))
                selected_group = (
                    source_group if side == "source" else destination_group
                )
                has_order = Order.objects.filter(
                    user=request.user, OrderGroup=selected_group, OrderIPOName=ipo
                ).exists()
                accounting_membership = Accounting.objects.filter(
                    user=request.user, group=selected_group, ipo=ipo, is_deleted=False
                )
                has_accounting = accounting_membership.exists()
                if not (has_order or has_accounting):
                    raise ValidationError(
                        f"{ipo.IPOName} is not available for {selected_group.GroupName}."
                    )
                if ipo.id in seen_ids:
                    raise ValidationError(f"Duplicate {side} IPO selected.")
                seen_ids.add(ipo.id)
                amount = _parse_transaction_amount(item.get("amount"))
                amount_type = item.get("amount_type")
                if amount_type not in VALID_TRANSACTION_TYPES:
                    raise ValidationError(f"Invalid {side} amount type.")

                order_total = Order.objects.filter(
                    user=request.user,
                    OrderGroup=selected_group,
                    OrderIPOName=ipo,
                ).aggregate(total=Sum("Amount"))["total"] or Decimal("0.00")
                accounting_query = Accounting.objects.filter(
                    user=request.user,
                    group=selected_group,
                    ipo=ipo,
                    is_deleted=False,
                )
                if edit_batch_id:
                    accounting_query = accounting_query.exclude(
                        transfer_batch_id=edit_batch_id
                    )
                accounting_total = accounting_query.aggregate(
                    total=Sum(Case(
                        When(amount_type="credit", then=F("amount")),
                        When(amount_type="debit", then=-F("amount")),
                        output_field=DecimalField(),
                    ))
                )["total"] or Decimal("0.00")
                outstanding = (
                    Decimal(str(order_total)) - Decimal(str(accounting_total))
                ).quantize(MONEY_QUANTUM)
                outstanding_type = "debit" if outstanding < 0 else "credit"
                if outstanding == Decimal("0.00"):
                    raise ValidationError(
                        f"{ipo.IPOName} has no outstanding balance for {selected_group.GroupName}."
                    )
                if amount_type != outstanding_type:
                    raise ValidationError(
                        f"{ipo.IPOName} must use {outstanding_type.title()}."
                    )
                if amount > abs(outstanding):
                    raise ValidationError(
                        f"{ipo.IPOName} allocation cannot exceed its original balance of ₹{abs(outstanding):.2f}."
                    )
                gross_total += amount
                signed_total += amount if amount_type == "credit" else -amount
                validated.append((ipo, amount, amount_type))

            jv_data = payload.get(f"{side}_jv")
            validated_jv = None
            if jv_data is not None:
                if not isinstance(jv_data, dict):
                    raise ValidationError(f"Invalid {side} JV allocation.")
                jv_amount = _parse_transaction_amount(jv_data.get("amount"))
                jv_type = jv_data.get("amount_type")
                if jv_type not in VALID_TRANSACTION_TYPES:
                    raise ValidationError(f"Invalid {side} JV amount type.")
                gross_total += jv_amount
                signed_total += jv_amount if jv_type == "credit" else -jv_amount
                validated_jv = (jv_amount, jv_type)

            if not validated and validated_jv is None:
                raise ValidationError(f"No {side} allocation was provided.")

            expected_total = (
                master_amount if expected_type == "credit" else -master_amount
            )
            if gross_total > master_amount:
                raise ValidationError(
                    f"{side.capitalize()} allocation exceeds the transfer amount."
                )
            if signed_total.quantize(MONEY_QUANTUM) != expected_total:
                raise ValidationError(
                    f"{side.capitalize()} allocation must equal the transfer amount."
                )
            return validated, validated_jv

        source_allocations, source_jv = validate_allocations(
            payload.get("source_allocations"), "source", source_type
        )
        destination_items = payload.get("destination_allocations")
        destination_allocations, destination_jv = validate_allocations(
            destination_items, "destination", destination_type
        )
        source_accounts = {
            (source_group.id, ipo.id) for ipo, amount, amount_type in source_allocations
        }
        destination_accounts = {
            (destination_group.id, ipo.id)
            for ipo, amount, amount_type in destination_allocations
        }
        if source_accounts & destination_accounts:
            raise ValidationError(
                "The same group and IPO cannot be on both sides of a transfer."
            )

        source_label = source_group.GroupName
        destination_label = destination_group.GroupName
        suffix = f" - {user_remark}" if user_remark else ""
        transfer_batch_id = edit_batch_id or uuid.uuid4()
        records = []
        for ipo, amount, amount_type in source_allocations:
            records.append(Accounting(
                user=request.user,
                ipo=ipo,
                group=source_group,
                amount=amount,
                amount_type=amount_type,
                remark=(f"Transfer to {destination_label}{suffix}")[:250],
                date_time=transfer_date,
                jv=False,
                transfer_batch_id=transfer_batch_id,
            ))

        if source_jv:
            amount, amount_type = source_jv
            records.append(Accounting(
                user=request.user,
                ipo=None,
                group=source_group,
                amount=amount,
                amount_type=amount_type,
                remark=(f"Transfer excess to {destination_label}{suffix}")[:250],
                date_time=transfer_date,
                jv=True,
                transfer_batch_id=transfer_batch_id,
            ))

        for ipo, amount, amount_type in destination_allocations:
            records.append(Accounting(
                user=request.user,
                ipo=ipo,
                group=destination_group,
                amount=amount,
                amount_type=amount_type,
                remark=(f"Transfer from {source_label}{suffix}")[:250],
                date_time=transfer_date,
                jv=False,
                transfer_batch_id=transfer_batch_id,
            ))

        if destination_jv:
            amount, amount_type = destination_jv
            records.append(Accounting(
                user=request.user,
                ipo=None,
                group=destination_group,
                amount=amount,
                amount_type=amount_type,
                remark=(f"JV transfer from {source_label}{suffix}")[:250],
                date_time=transfer_date,
                jv=True,
                transfer_batch_id=transfer_batch_id,
            ))

        with transaction.atomic():
            if edit_batch_id:
                existing_batch.delete()
            Accounting.objects.bulk_create(records)

        return JsonResponse({
            "status": "success",
            "message": (
                f"Updated {len(records)} balanced transfer entries."
                if edit_batch_id else
                f"Created {len(records)} balanced transfer entries."
            ),
        })
    except json.JSONDecodeError:
        return JsonResponse(
            {"status": "error", "message": "Invalid transfer data."}, status=400
        )
    except ValidationError as exc:
        return JsonResponse(
            {"status": "error", "message": exc.messages[0]}, status=400
        )
    except Exception as exc:
        traceback.print_exc()
        message = str(exc) if settings.DEBUG else "Server error while saving transfer."
        return JsonResponse(
            {"status": "error", "message": message}, status=500
        )


@login_required
def get_transfer_batch(request, batch_id):
    entries = list(Accounting.objects.filter(
        user=request.user,
        transfer_batch_id=batch_id,
        is_deleted=False,
    ).select_related("group", "ipo").order_by("id"))
    if not entries:
        return JsonResponse(
            {"status": "error", "message": "Transfer batch was not found."},
            status=404,
        )

    group_ids = list(dict.fromkeys(
        entry.group_id for entry in entries if entry.group_id is not None
    ))
    if len(group_ids) != 2:
        return JsonResponse(
            {"status": "error", "message": "This transfer cannot be edited because its groups are incomplete."},
            status=400,
        )

    source_group_id, destination_group_id = group_ids
    source_entries = [entry for entry in entries if entry.group_id == source_group_id]
    destination_entries = [entry for entry in entries if entry.group_id == destination_group_id]
    source_type = source_entries[0].amount_type
    master_amount = sum((entry.amount for entry in source_entries), Decimal("0.00"))
    source_group = source_entries[0].group
    destination_group = destination_entries[0].group

    remark = ""
    first_remark = source_entries[0].remark or ""
    prefixes = (
        f"Transfer to {destination_group.GroupName}",
        f"Transfer excess to {destination_group.GroupName}",
    )
    for prefix in prefixes:
        if first_remark.startswith(prefix):
            remark = first_remark[len(prefix):]
            if remark.startswith(" - "):
                remark = remark[3:]
            break

    def serialize_allocations(batch_entries):
        return [
            {
                "ipo_id": entry.ipo_id,
                "amount": str(entry.amount),
                "amount_type": entry.amount_type,
            }
            for entry in batch_entries if entry.ipo_id is not None
        ]

    return JsonResponse({
        "status": "success",
        "data": {
            "transfer_batch_id": str(batch_id),
            "source_group_id": source_group_id,
            "destination_group_id": destination_group_id,
            "source_type": source_type,
            "master_amount": str(master_amount),
            "remark": remark,
            "date_time": timezone.localtime(entries[0].date_time).strftime("%Y-%m-%dT%H:%M:%S"),
            "source_allocations": serialize_allocations(source_entries),
            "destination_allocations": serialize_allocations(destination_entries),
        },
    })


@login_required
def get_transfer_group_ipos(request, group_id):
    """Return IPOs with an outstanding balance for the selected group."""
    try:
        group = _get_owned_group(request.user, group_id)
        exclude_batch_id = request.GET.get("exclude_batch")
        if exclude_batch_id:
            try:
                exclude_batch_id = uuid.UUID(str(exclude_batch_id))
            except (ValueError, TypeError, AttributeError):
                raise ValidationError("Invalid transfer batch.")
            if not Accounting.objects.filter(
                user=request.user, transfer_batch_id=exclude_batch_id
            ).exists():
                raise ValidationError("Transfer batch was not found.")
        order_ipo_ids = Order.objects.filter(
            user=request.user,
            OrderGroup=group,
        ).values_list("OrderIPOName_id", flat=True).distinct()
        accounting_membership = Accounting.objects.filter(
            user=request.user,
            group=group,
            ipo_id__isnull=False,
            is_deleted=False,
        )
        if exclude_batch_id:
            accounting_membership = accounting_membership.exclude(
                transfer_batch_id=exclude_batch_id
            )
        accounting_ipo_ids = accounting_membership.values_list(
            "ipo_id", flat=True
        ).distinct()
        edited_batch_ipo_ids = []
        if exclude_batch_id:
            edited_batch_ipo_ids = Accounting.objects.filter(
                user=request.user,
                group=group,
                transfer_batch_id=exclude_batch_id,
                ipo_id__isnull=False,
            ).values_list("ipo_id", flat=True).distinct()
        ipo_ids = (
            set(order_ipo_ids) |
            set(accounting_ipo_ids) |
            set(edited_batch_ipo_ids)
        )
        ipos = CurrentIpoName.objects.filter(
            user=request.user,
            id__in=ipo_ids,
        ).order_by("IPOName")
        order_totals = Order.objects.filter(
            user=request.user, OrderGroup=group, OrderIPOName_id__in=ipo_ids
        ).values("OrderIPOName_id").annotate(total=Sum("Amount"))
        order_amounts = {
            row["OrderIPOName_id"]: Decimal(str(row["total"] or 0))
            for row in order_totals
        }
        accounting_totals_query = Accounting.objects.filter(
            user=request.user, group=group, ipo_id__in=ipo_ids, is_deleted=False
        )
        if exclude_batch_id:
            accounting_totals_query = accounting_totals_query.exclude(
                transfer_batch_id=exclude_batch_id
            )
        accounting_totals = accounting_totals_query.values("ipo_id").annotate(
            total=Sum(Case(
                When(amount_type="credit", then=F("amount")),
                When(amount_type="debit", then=-F("amount")),
                output_field=DecimalField(),
            ))
        )
        paid_amounts = {
            row["ipo_id"]: Decimal(str(row["total"] or 0))
            for row in accounting_totals
        }
        ipo_data = []
        for ipo in ipos:
            due = (
                order_amounts.get(ipo.id, Decimal("0")) -
                paid_amounts.get(ipo.id, Decimal("0"))
            ).quantize(MONEY_QUANTUM)
            if due == Decimal("0.00"):
                continue
            ipo_data.append({
                "ipo_id": ipo.id,
                "ipo_name": ipo.IPOName,
                "due_amount": str(due),
            })

        return JsonResponse({"status": "success", "data": ipo_data})
    except ValidationError as exc:
        return JsonResponse(
            {"status": "error", "message": exc.messages[0]}, status=400
        )


@login_required
def get_group_dues(request, group_id):
    """
    API endpoint that returns the due amount for each IPO in a specific group.
    Used by the Add Payment modal for bulk auto-allocation.
    """
    try:
        from django.db.models import Sum, Case, When, F, DecimalField
        from django.http import JsonResponse
        from .models import GroupDetail, CurrentIpoName, Order, Accounting
        
        group = GroupDetail.objects.get(id=group_id, user=request.user)
        ipos = CurrentIpoName.objects.filter(user=request.user)
        
        # 1. Fetch Order Totals (How much was billed)
        order_totals = (
            Order.objects.filter(user=request.user, OrderGroup=group)
            .values("OrderIPOName_id")
            .annotate(total=Sum("Amount"))
        )
        order_dict = {row["OrderIPOName_id"]: float(row["total"] or 0) for row in order_totals}
        
        # 2. Fetch Accounting Totals (How much was paid)
        accounting_totals = (
            Accounting.objects.filter(user=request.user, group=group, is_deleted=False)
            .values("ipo_id")
            .annotate(
                total=Sum(
                    Case(
                        When(amount_type='credit', then=F('amount')),
                        When(amount_type='debit', then=-F('amount')),
                        output_field=DecimalField()
                    )
                )
            )
        )
        accounting_dict = {row["ipo_id"]: float(row["total"] or 0) for row in accounting_totals}
        
        # 3. Calculate Dues
        due_data = []
        for ipo in ipos:
            billed = order_dict.get(ipo.id, 0.0)
            paid = accounting_dict.get(ipo.id, 0.0)
            due = billed - paid
            
            # Only include IPOs with a non-zero balance (exactly like the old modal logic)
            if abs(due) > 0.001:
                due_data.append({
                    "ipo_id": ipo.id,
                    "ipo_name": ipo.IPOName,
                    "due_amount": round(due, 2)
                })
                    
        return JsonResponse({"status": "success", "data": due_data})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def send_group_email(request,group_data, IPOName, entry, record_type, user_email, user_app_pw, request_user,OrderType):
    try:
        group = unquote(group_data['name'])
        group_email = group_data['email']
        
        GP = GroupDetail.objects.get(GroupName=group, user=request_user)
        gid = GP.id
        if not group_email:
            group_email = GP.Email
        if not group_email:
            messages.info(request, f"Email ID is not avaliable for '{group}' Group ,")
            return  # Skip if no email
        try:
            validate_email(group_email)
        except ValidationError:
            messages.info(request, f"Failed to share Group Details: '{group}' has an invalid email address.")
            return # Skip if not valid email

        filtered_entry = entry.filter(Order__OrderGroup_id=gid)
        csv_buffer = StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(['Group', 'IPO Type', 'Investor Type', 'Rate', 'PAN No',
                         'Client Name', 'AllotedQty', 'Demat Number', 'Application Number', 'Order Date', 'Order Time'])

        if record_type == 'Pending PAN':
            rows = filtered_entry.filter(OrderDetailPANNo_id=None)
        else:
            rows = filtered_entry

        for member in rows.values_list('Order__OrderGroup__GroupName', 'Order__OrderCategory', 'Order__InvestorType',
                                       'Order__Rate', 'OrderDetailPANNo__PANNo', 'OrderDetailPANNo__Name', 'AllotedQty',
                                       'DematNumber', 'ApplicationNumber', 'Order__OrderDate', 'Order__OrderTime'):
            List = list(member)
            List[9] = str(List[9].strftime('%d/%m/%Y'))
            if List[7] != "":
                List[7] = "'" + List[7]
            writer.writerow(tuple(List))

        csv_content = csv_buffer.getvalue()
        msg = MIMEMultipart()
        msg['Subject'] = 'Update Required – Missing Details in Attached File'
        msg['From'] = user_email
        msg['To'] = group_email
        
        if OrderType == "BUY":
        
            body = f"""\
                Dear {group},\n
                Please find the attached document which requires your input. We kindly ask you to provide the following missing information:

                • PAN Number (Mandatory)
                • Name
                • Client ID
                • DP ID
                • Application Number

                Once completed, please reply to this email with the updated file.

                """
        else:
            body = f"""\
                Dear {group},\n
                Please find attached the Excel related to your recent orders.\n

                Regards,\n
                
                """
        
        
        msg.attach(MIMEText(body, 'plain'))

        part = MIMEApplication(csv_content, Name=f'{group}_{IPOName.IPOName}.csv')
        part['Content-Disposition'] = f'attachment; filename="{group}_{IPOName.IPOName}.csv"'
        msg.attach(part)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(user_email, user_app_pw)
            smtp.send_message(msg)

    except ValidationError:
        messages.info(request, f"Invalid email: {group_email}")
    except Exception as e:
        messages.info(request, f"Failed to send email to group {group}: {e}")

def GroupBillShare(request, IPOid):
    if request.method == 'POST':
        # Ensure the user is authenticated to get their email
        if not request.user.is_authenticated:
            messages.error(request, 'You must be logged in to share bills.')
            return redirect('login_url') # Redirect to your login page

        group_name = request.POST.get('GroupName', 'Default Group')

        # Get the currently logged-in user's email
        # This email will be used as the 'From' address in the email header.
        EMAIL_ADDRESS = "dipakbhadaniya09@gmail.com"  # Your personal email
        EMAIL_PASSWORD = "dpxw slhx hqiy dtyu"    # App password (not your login password)

        subject = f"Bill for {group_name} - IPO ID: {IPOid}"
        message = f"""
        Dear Customer,

        Please find the bill details for {group_name} related to IPO ID {IPOid}.

        [Insert actual bill content here.]

        Thank you.
        """
        # The 'from_email' parameter is set to the current user's email
        recipient_list = ['bhadaniyadb2001@gmail.com'] # Replace with actual recipient email(s)

        try:
            msg = MIMEMultipart()  # Change EmailMessage to MIMEMultipart
            msg['Subject'] = subject
            msg['From'] = EMAIL_ADDRESS
            msg['To'] = 'bhadaniyadb2001@gmail.com'  # Change to the receiver's email
            
            text_content = MIMEText(message)
            msg.attach(text_content)
            
            file_path = "home/views.py"  # Replace with the path to your file

            with open(file_path, 'rb') as f:
                file_data = f.read()
                file_name = f.name

            attached_file = MIMEApplication(file_data, _subtype="json")  # Adjust _subtype if necessary (e.g., 'pdf', 'jpeg')
            attached_file.add_header('Content-Disposition', 'attachment', filename=file_name)
            msg.attach(attached_file)

            # Send the email using Gmail's SMTP server
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                smtp.send_message(msg)
            
            messages.success(request, f'Bill for {group_name} shared successfully from {EMAIL_ADDRESS} to {", ".join(recipient_list)}!')
        except Exception as e:
            messages.error(request, f'Failed to share bill: {e}')

        return redirect('Status', IPOid=IPOid)
    else:
        messages.error(request, 'Invalid request method for sharing bill.')
        return redirect('Status', IPOid=IPOid)

@csrf_exempt
def Share_AppDetails(request):
    if request.method == 'POST':
        group_name_list_json = request.POST.get('selected_records', 'Default Group') 
        group_name_list = json.loads(group_name_list_json)
        record_type = request.POST.get('record_type','All Record')
        IPO_id = request.POST.get('IPO_id','')
        OrderType = request.POST.get('OrderType','')
        
        Custom_user = CustomUser.objects.get(username=request.user)
        user_email = Custom_user.email
        user_app_pw = Custom_user.AppPassword  
        # user_app_pw = ''
        
        if not user_email:
            messages.info(request, f'Email configuration is pending for {request.user}')
            return JsonResponse('Success', safe=False)
        if not user_app_pw:
            messages.info(request, f'Email configuration is pending for {request.user}')
            return JsonResponse('Success', safe=False)
        
        IPOName = CurrentIpoName.objects.get(id=IPO_id, user=request.user)
        entry = OrderDetail.objects.filter(
            user=request.user, Order__OrderIPOName_id=IPO_id)
        
        if OrderType == "BUY":
                entry = entry.filter(Order__OrderType="BUY")
        if OrderType == "SELL":
            entry = entry.filter(Order__OrderType="SELL")
                
        # for group_data in group_name_list:
        #     group = unquote(group_data['name'])
        #     group_email = group_data['email']
            
        #     GP = GroupDetail.objects.get(
        #         GroupName=group, user=request.user)
            
        #     gid = GP.id
        #     if not group_email:
        #         group_email = GP.Email
            
        #     if not group_email:
        #         messages.error(request, f"Failed to share Group Details: '{group}' has no associated email address.")
        #         continue
        #     try:
        #         validate_email(group_email)
        #     except ValidationError:
        #         messages.error(request, f"Failed to share Group Details: '{group}' has an invalid email address.")
        #         continue
            
        #     entry_forGp = entry.filter(Order__OrderGroup_id=gid)
            
        #     csv_buffer = StringIO()
                
        #     writer = csv.writer(csv_buffer)
        #     writer.writerow(['Group', 'IPO Type', 'Investor Type', 'Rate', 'PAN No',
        #                     'Client Name', 'AllotedQty', 'Demat Number', 'Application Number', 'Order Date', 'Order Time'])

        #     if record_type == 'Pending PAN':
        #         for member in entry_forGp.filter(OrderDetailPANNo_id=None).values_list('Order__OrderGroup__GroupName', 'Order__OrderCategory', 'Order__InvestorType','Order__Rate', 'OrderDetailPANNo__PANNo', 'OrderDetailPANNo__Name', 'AllotedQty','DematNumber', 'ApplicationNumber', 'Order__OrderDate', 'Order__OrderTime'):
        #             List = list(member)
        #             List[9] = str(List[9].strftime('%d/%m/%Y'))
        #             if List[7] != "":
        #                 List[7] = "'" + List[7]
        #             member = tuple(List)
        #             writer.writerow(member)
        #     else:
        #         for member in entry_forGp.filter().values_list('Order__OrderGroup__GroupName', 'Order__OrderCategory', 'Order__InvestorType','Order__Rate', 'OrderDetailPANNo__PANNo', 'OrderDetailPANNo__Name', 'AllotedQty','DematNumber', 'ApplicationNumber', 'Order__OrderDate', 'Order__OrderTime'):
        #             List = list(member)
        #             List[9] = str(List[9].strftime('%d/%m/%Y'))
        #             if List[7] != "":
        #                 List[7] = "'" + List[7]
        #             member = tuple(List)
        #             writer.writerow(member)
                
        #     csv_content = csv_buffer.getvalue()  
            
        #     # recipient_list = [group_email]
            
        #     try:
        #         msg = MIMEMultipart()  # Change EmailMessage to MIMEMultipart
        #         msg['Subject'] = f'IPO Details for Group: {group} ({IPOName.IPOName})'
        #         msg['From'] = user_email
        #         msg['To'] = group_email 
                
        #         msg.attach(MIMEText('Please find the attached IPO details CSV.', 'plain'))
                
        #         part = MIMEApplication(csv_content, Name=f'{group}_{IPOName.IPOName}.csv')
        #         part['Content-Disposition'] = f'attachment; filename="{group}_{IPOName.IPOName}.csv"'
        #         msg.attach(part)
                
        #         with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        #             smtp.login(user_email, user_app_pw)
        #             smtp.send_message(msg)
                
        #         # messages.success(request, f'Bill for {group} shared successfully from {user_email} to {", ".join(recipient_list)}!')
                
        #     except Exception as e:
        #         traceback.print_exc()
        #         messages.error(request, f'Failed to share Group Details: {e}')
        
        # if group_name_list:        
        threads = []
        for group_data in group_name_list:
            t = threading.Thread(target=send_group_email, args=(request,group_data, IPOName, entry, record_type, user_email, user_app_pw, request.user,OrderType))
            t.start()
            threads.append(t)
            
        for t in threads:
            t.join()
        
        return JsonResponse('Success', safe=False)
    
#PAN UPDATE LINK
def generate_shared_link(request):
    if request.method == "POST":
        ipo_id = request.POST.get('ipo_id')
        group_name = request.POST.get('group_name')
        expiry_str = request.POST.get('expiry_at')
        
        # 1. Convert string to aware datetime
        expiry_dt = make_aware(datetime.strptime(expiry_str, '%Y-%m-%dT%H:%M'))
        
        # 2. Get the actual GroupDetail instance (use .first() to get the object, not a list)
        group_instance = GroupDetail.objects.filter(user=request.user, GroupName=group_name).first()
        
        if not group_instance and group_name != "All":
            return JsonResponse({'status': 'fail', 'message': 'Group not found'})

        # 3. Create the link record
        # Note: Use ipo_id=ipo_id to assign by ID directly
        link_obj = SharedLink.objects.create(
            user=request.user,
            ipo_id=ipo_id, 
            group=group_instance, # This is now the actual instance
            expiry_at=expiry_dt
        )
        
        # Create full URL with the UUID
        full_url = request.build_absolute_uri(f'/access-link/{link_obj.id}/')
        
        return JsonResponse({'status': 'success', 'link': full_url})

def order_detail_view(request, IPOid, Ordtyp, GrpName=None, OrderCategory=None, InvestorType=None, OrderDate=None, OrderTime=None):
    
    has_session_access = request.session.get(f'access_auth_{IPOid}', False)
    if not request.user.is_authenticated and not has_session_access:
        return redirect('login') # Block unauthorized people
    
    if has_session_access:
        user = request.session[f'link_owner_{IPOid}']
        link_id = request.session[f'access']
        Group_id = SharedLink.objects.get(id=link_id).group
        entry = OrderDetail.objects.filter(
            user=user, Order__OrderIPOName_id=IPOid, Order__OrderType=Ordtyp)
        Group = GroupDetail.objects.filter(
            user=user,GroupName=Group_id)
        IPOName = CurrentIpoName.objects.get(id=IPOid, user=user)
        
    else:
        if request.user.groups.all()[0].name == 'Broker':
            entry = OrderDetail.objects.filter(
                user=request.user, Order__OrderIPOName_id=IPOid, Order__OrderType=Ordtyp)
            Group = GroupDetail.objects.filter(
                user=request.user)
            IPOName = CurrentIpoName.objects.get(id=IPOid, user=request.user)
        else:
            entry = OrderDetail.objects.filter(
                user=request.user.Broker_id, Order__OrderIPOName_id=IPOid, Order__OrderGroup_id=request.user.Group_id, Order__OrderType=Ordtyp)
            Group = GroupDetail.objects.filter(
                user=request.user.Broker_id, id=request.user.Group_id)
            
            IPOName = CurrentIpoName.objects.get(
                id=IPOid, user=request.user.Broker_id)
        
    group_names_list = []
    Panding_Pan_GroupList = []
    
    entry_for_gp = entry.select_related('OrderDetailPANNo__Group', 'Order__OrderGroup')
    for order_detail_entry in entry_for_gp:
        if order_detail_entry.OrderDetailPANNo:  # Check if OrderDetailPANNo is not null
            group_name = order_detail_entry.OrderDetailPANNo.Group.GroupName
            Group_emial = order_detail_entry.OrderDetailPANNo.Group.Email
        else:
            group_name = order_detail_entry.Order.OrderGroup.GroupName
            Group_emial = order_detail_entry.Order.OrderGroup.Email
            if not any(g['group_name'] == group_name for g in Panding_Pan_GroupList):
                Panding_Pan_GroupList.append({'group_name':group_name,'Group_emial':Group_emial})
        
        if not any(g['group_name'] == group_name for g in group_names_list):
            group_names_list.append({'group_name':group_name,'Group_emial':Group_emial})
        
    Od_time = OrderTime
    Od_Date = OrderDate
    if OrderDate == "None":
        OrderDate = None

    if OrderTime == "None":
        OrderTime = None 

    if OrderDate != None:
        OrderDate = OrderDate[0:4] +'-'+ OrderDate[4:6]+'-'+ OrderDate[6:8]
        entry = entry.filter(Order__OrderDate = OrderDate)        

    if OrderTime != None:
        OrderTime = OrderTime[0:2] + ':' + OrderTime[2:4] + ':' + OrderTime[4:6]
        entry = entry.filter(Order__OrderTime = OrderTime)

    AppTotal=len(entry)
    Appwithoutpan=len(entry.filter(OrderDetailPANNo_id=None))

    if GrpName == None and OrderCategory == None and InvestorType == None:
        Groupfilter = 'All'
        IPOTypefilter = 'All'
        InvestorTypeFilter = 'All'
        
        if IPOTypefilter == 'All' and Groupfilter=='All' and InvestorTypeFilter=="All":
            pass
        elif IPOTypefilter == 'All' and  Groupfilter=='All':
            entry =  entry.filter(Order__InvestorType=InvestorTypeFilter)
        elif IPOTypefilter == 'All' and InvestorTypeFilter=='All':   
            entry = entry.filter(Order__OrderGroup__GroupName=Groupfilter)
        elif InvestorTypeFilter=='All' and  Groupfilter=='All':
            entry =  entry.filter(Order__OrderCategory=IPOTypefilter)
        elif IPOTypefilter == 'All':   
            entry = entry.filter(Order__OrderGroup__GroupName=Groupfilter, Order__InvestorType=InvestorTypeFilter)
        elif Groupfilter=='All':
            entry =  entry.filter(Order__OrderCategory=IPOTypefilter, Order__InvestorType=InvestorTypeFilter)
        elif InvestorTypeFilter=='All':
            entry =  entry.filter(Order__OrderCategory=IPOTypefilter, Order__OrderGroup__GroupName=Groupfilter)
        else:
            entry =  entry.filter(Order__OrderCategory=IPOTypefilter, Order__OrderGroup__GroupName=Groupfilter,Order__InvestorType=InvestorTypeFilter)
        AppTotal=len(entry)
        Appwithoutpan=len(entry.filter(OrderDetailPANNo_id=None))
    
    else:
        Groupfilter = unquote(GrpName)
        IPOTypefilter = unquote(OrderCategory)
        InvestorTypeFilter = InvestorType

        if IPOTypefilter == 'All' and Groupfilter=='All' and InvestorTypeFilter=="All":
            pass
        elif IPOTypefilter == 'All' and  Groupfilter=='All':
            entry =  entry.filter(Order__InvestorType=InvestorTypeFilter)
        elif IPOTypefilter == 'All' and InvestorTypeFilter=='All':   
            entry = entry.filter(Order__OrderGroup__GroupName=Groupfilter)
        elif InvestorTypeFilter=='All' and  Groupfilter=='All':
            entry =  entry.filter(Order__OrderCategory=IPOTypefilter)
        elif IPOTypefilter == 'All':   
            entry = entry.filter(Order__OrderGroup__GroupName=Groupfilter, Order__InvestorType=InvestorTypeFilter)
        elif Groupfilter=='All':
            entry =  entry.filter(Order__OrderCategory=IPOTypefilter, Order__InvestorType=InvestorTypeFilter)
        elif InvestorTypeFilter=='All':
            entry =  entry.filter(Order__OrderCategory=IPOTypefilter, Order__OrderGroup__GroupName=Groupfilter)
        else:
            entry =  entry.filter(Order__OrderCategory=IPOTypefilter, Order__OrderGroup__GroupName=Groupfilter,Order__InvestorType=InvestorTypeFilter)
        AppTotal=len(entry)
        Appwithoutpan=len(entry.filter(OrderDetailPANNo_id=None))

    if request.method == "POST":
        if has_session_access:
            user = request.session[f'link_owner_{IPOid}']
            entry = OrderDetail.objects.filter(
                    user=user, Order__OrderIPOName_id=IPOid, Order__OrderType=Ordtyp)
        else:
            if request.user.groups.all()[0].name == 'Broker':
                entry = OrderDetail.objects.filter(
                    user=request.user, Order__OrderIPOName_id=IPOid, Order__OrderType=Ordtyp)
            else:
                entry = OrderDetail.objects.filter(
                    user=request.user.Broker_id, Order__OrderIPOName_id=IPOid, Order__OrderGroup_id=request.user.Group_id, Order__OrderType=Ordtyp)
        
        Groupfilter = request.POST.get('Groupfilter', '')
        IPOTypefilter = request.POST.get('IPOTypefilter', '')
        InvestorTypeFilter = request.POST.get('InvestorTypeFilter', '')
        if Groupfilter == '' or Groupfilter == None:
            Groupfilter = 'All'
        if IPOTypefilter == '' or IPOTypefilter == None:
            IPOTypefilter = 'All'
        if InvestorTypeFilter == '' or InvestorTypeFilter == None:
            InvestorTypeFilter = 'All'

        if is_valid_queryparam(Groupfilter) and Groupfilter != 'All':
            entry = entry.filter(Order__OrderGroup__GroupName=Groupfilter)
        if is_valid_queryparam(IPOTypefilter) and IPOTypefilter != 'All':
            entry = entry.filter(Order__OrderCategory=IPOTypefilter)
        if is_valid_queryparam(InvestorTypeFilter) and InvestorTypeFilter != 'All':
            entry = entry.filter(Order__InvestorType=InvestorTypeFilter)
        
        Groupfilter = Groupfilter
        IPOTypefilter = IPOTypefilter
        InvestorTypeFilter = InvestorTypeFilter
        AppTotal=len(entry)
        Appwithoutpan=len(entry.filter(OrderDetailPANNo_id=None))

        if OrderDate != None and OrderTime!= None:
            OrderDate = OrderDate[0:4] + OrderDate[5:7] + OrderDate[8:10]
            OrderTime = OrderTime[0:2] + OrderTime[3:5] + OrderTime[6:8]
    
    page_obj = None
    try:
        page_size = request.POST.get('page_size')
        if page_size != '' and page_size != None:
            request.session['page_size'] = page_size
        else:
            page_size = request.session['page_size']
    except:
        page_size = request.session.get('page_size', 50)
        
    Data = []
    if has_session_access:
        user = request.session[f'link_owner_{IPOid}']
        entry = (
                entry
                .select_related("Order", "Order__OrderGroup", "OrderDetailPANNo", "OrderDetailPANNo__Group")
                .filter(user=user, Order__OrderIPOName_id=IPOid, Order__OrderType=Ordtyp)
                .order_by("Order__OrderGroup__GroupName", "-Order__OrderDate", "-Order__OrderTime", "-id")
            )
    else:
        if request.user.groups.all()[0].name == 'Broker':
            entry = (
                entry
                .select_related("Order", "Order__OrderGroup", "OrderDetailPANNo", "OrderDetailPANNo__Group")
                .filter(user=request.user, Order__OrderIPOName_id=IPOid, Order__OrderType=Ordtyp)
                .order_by("Order__OrderGroup__GroupName", "-Order__OrderDate", "-Order__OrderTime", "-id")
            )
        else:
            entry = (
                entry
                .select_related("Order", "Order__OrderGroup", "OrderDetailPANNo", "OrderDetailPANNo__Group")
                .filter(user=request.user.Broker_id, Order__OrderIPOName_id=IPOid, Order__OrderGroup_id=request.user.Group_id, Order__OrderType=Ordtyp)
                .order_by("Order__OrderGroup__GroupName", "-Order__OrderDate", "-Order__OrderTime", "-id")
            )

    entry = entry.order_by('-id')
    if entry is not None and entry.exists():
        if page_size == 'All':
            paginator = Paginator(entry,len(entry))
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
        else:
            paginator = Paginator(entry, page_size)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
        start_index = (page_obj.number - 1) * page_obj.paginator.per_page
        # for i,order_detail in enumerate(page_obj):
        #     entry_data = {
        #         'id':order_detail.id,
        #         'OrderGroup': order_detail.Order.OrderGroup,
        #         'OrderCategory': order_detail.Order.OrderCategory,
        #         'OrderType': order_detail.Order.OrderType,
        #         'InvestorType': order_detail.Order.InvestorType,
        #         'Rate': order_detail.Order.Rate,
        #         'PANNo': order_detail.OrderDetailPANNo.PANNo if (order_detail.OrderDetailPANNo and order_detail.OrderDetailPANNo.PANNo is not None) else '',   
        #         'Name': order_detail.OrderDetailPANNo.Name if (order_detail.OrderDetailPANNo and order_detail.OrderDetailPANNo.Name is not None) else '',   
        #         'AllotedQty': float(order_detail.AllotedQty) if (order_detail.AllotedQty is not None) else '',
        #         'DematNumber': order_detail.DematNumber if (order_detail and order_detail.DematNumber is not None) else '',   
        #         'ApplicationNumber': order_detail.ApplicationNumber if (order_detail and order_detail.ApplicationNumber is not None) else '',   
        #         'Date': order_detail.Order.OrderDate,
        #         'Time': order_detail.Order.OrderTime,
        #         'sr_no': start_index + i + 1,
        #         'Client_id':order_detail.OrderDetailPANNo.id if order_detail.OrderDetailPANNo is not None else '',
        #         'Alloted_qty':float(order_detail.AllotedQty) if (order_detail.AllotedQty is not None) else '',
        #         'Demate_number':order_detail.DematNumber if (order_detail and order_detail.DematNumber is not None) else '',
        #         'Application_Number':order_detail.ApplicationNumber if (order_detail and order_detail.ApplicationNumber is not None) else '',
        #         'client_Name': order_detail.OrderDetailPANNo.Name if (order_detail.OrderDetailPANNo and order_detail.OrderDetailPANNo.Name is not None) else ''  
        #         # Add other fields as needed
        #     }
        #     Data.append(entry_data)
        Data = []
        for i, order_detail in enumerate(page_obj, start=start_index + 1):
            pan = order_detail.OrderDetailPANNo  # cached from select_related
            order = order_detail.Order           # cached from select_related
            group = order.OrderGroup             # cached
            
            Data.append({
                'id': order_detail.id,
                'sr_no': i,
                'OrderGroup': group.GroupName if group else '',
                'OrderCategory': order.OrderCategory,
                'OrderType': order.OrderType,
                'InvestorType': order.InvestorType,
                'Rate': order.Rate,
                'PANNo': pan.PANNo if pan else '',
                'Name': pan.Name if pan else '',
                'Client_id': pan.id if pan else '',
                'client_Name': pan.Name if pan else '',
                'AllotedQty': float(order_detail.AllotedQty) if order_detail.AllotedQty is not None else '',
                'Alloted_qty': float(order_detail.AllotedQty) if order_detail.AllotedQty is not None else '',
                'DematNumber': order_detail.DematNumber or '',
                'Demate_number': order_detail.DematNumber or '',
                'ApplicationNumber': order_detail.ApplicationNumber or '',
                'Application_Number': order_detail.ApplicationNumber or '',
                'Remark': format_remark(order.remark) or "-",
                'Date': order.OrderDate,
                'Time': order.OrderTime,
            })

    else:
        paginator = Paginator([], 1)
        page_obj = paginator.get_page(1)
    
    df = pd.DataFrame.from_records(Data)
        
    html_table = "<table>\n"
    html_table = "<thead><tr style='text-align: center;'>"
    html_table += "<th>Sr No.</th>"
    html_table += "<th>Group</th>"
    html_table += "<th>Order Category</th>"
    if IPOName.IPOType == "MAINBOARD":
        html_table += "<th>Investor Type</th>"
    html_table += "<th>Rate</th>"
    html_table += "<th data-sort='input'>PAN No<span style='color: red;'>*</span></th>"
    html_table += "<th data-sort='input'>Client Name</th>"
    html_table += "<th data-sort='input'>Alloted Qty</th>"
    html_table += "<th data-sort='input'>Demat No</th>"
    html_table += "<th data-sort='input'>Application No</th>"
    html_table += "<th>Date and Time</th>"
    html_table += "<th>Remark</th>"
    html_table += "</tr></thead>\n" 
    
    html_table += "<tbody style='text-align: center;white-space: nowrap;'>"
    if df.empty:
        column_count = 11 if IPOName.IPOType == "MAINBOARD" else 10
        html_table += f"<tr class='odd'><td colspan='{column_count}' valign='top' class='dataTables_empty'>No data available</td></tr>"
    else:
        for i, row in df.iterrows():
            datetime_str  = f"{row.Date} {row.Time}"
            datetime_obj = datetime.strptime(datetime_str , "%Y-%m-%d %H:%M:%S")
            formatted_datetime = datetime_obj.strftime("%b. %d, %Y %I:%M %p")
            html_table += f"<td>{row.sr_no}</td>"
            html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','{row.OrderGroup}','All','All','{Ordtyp}')\" title=\"Double-click to filter by this Group\">{row.OrderGroup}</td>"
            html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','All','{row.OrderCategory}','All','{Ordtyp}')\" title=\"Double-click to filter by this Group\">{row.OrderCategory}</td>"
            if IPOName.IPOType == 'MAINBOARD':
                html_table += f"<td ondblclick=\"sendPostRequest('{IPOid}','All','All','{row.InvestorType}','{Ordtyp}')\" title=\"Double-click to filter by this Group\">{row.InvestorType}</td>"
            html_table += f"<td>{row.Rate}</td>"
            html_table += f"<td style='width:185px;'><input class='auto' type='text' style='text-transform: uppercase;  width:165px;' maxlength='10' minlength='10' name='PAN_{row.id}_{row.Rate}_{row.Client_id}_{row.Alloted_qty}_{row.Demate_number}_{row.Application_Number}_{row.client_Name}' id='PAN_{ row.id }' onclick='functiontest({row.id})' value='{row.PANNo}' onfocus='hideTooltip({ row.id })' onblur='checkPAN({ row.id })'><div id='tooltip_{ row.id }' class='Shadow1' style='display:none;'>Invalid PAN number</div></td>"
            html_table += f"<td style='width:185px;'><input class='auto1' type='text' style='width:165px;' name='clientname_{row.id}' value='{row.Name}' id='clientname_{row.id}' oninput='sanitizeInput(this)' onblur='checkValidChars(this, \"tooltip_app_{row.id}\")' ><div id='clientname_tooltip_{row.id}' class='Shadow1' style='display:none; color:red; font-size:12px;'>Only letters, numbers, and . - & / @ _ are allowed</div></td>"
            if row.AllotedQty != '':
                html_table += f"<td style='width:90px;'><input type='text' onkeypress='return event.charCode >= 48 && event.charCode <= 57 || event.charCode == 46' style='width: 55px;' name='allotedqty_{row.id}' value='{int(row.AllotedQty) if row.AllotedQty.is_integer() else row.AllotedQty}'></td>"
            else:
                html_table += f"<td style='width:90px;'><input type='text' onkeypress='return event.charCode >= 48 && event.charCode <= 57 || event.charCode == 46' style='width: 55px;' name='allotedqty_{row.id}' value=''></td>"
            html_table += f"<td style='width:185px;'><input type='text' style='width:165px;' name='DematNo_{row.id}' oninput='sanitizeInput(this)' onblur='checkValidChars(this, \"tooltip_app_{row.id}\")'  value='{row.DematNumber}'></td>"
            html_table += f"<td style='width:185px;'><input type='text' style='width:165px;' name='Application_{row.id}' oninput='sanitizeInput(this)' onblur='checkValidChars(this, \"tooltip_app_{row.id}\")' value='{row.ApplicationNumber}'></td>"
            html_table += f"<td>{formatted_datetime}</td>"
            safe_remark = row.Remark.replace("'", "\\'").replace('"', '&quot;') if row.Remark else ""
            html_table += f"<td style='white-space: nowrap; max-width: 300px; overflow: hidden; text-overflow: ellipsis; cursor: pointer; outline: none;' tabindex='0' onclick=\"this.style.whiteSpace=this.style.whiteSpace==='normal'?'nowrap':'normal'\" onblur=\"this.style.whiteSpace='nowrap'\" title='{safe_remark}'>{row.Remark}</td>"
            html_table += "</tr>\n"
        
    html_table += "</tbody>"
    html_table += "</table>"    
    if not has_session_access:
        PRI_limit  = CustomUser.objects.get(username = request.user)
        is_premium_user = PRI_limit.Allotment_access    
        
        is_customer = request.user.groups.filter(name='Customer').exists()
    else:
        is_customer = False
        is_premium_user = False
    
    # Group = 

    if(Ordtyp == 'BUY'):
        return render(request, 'OrderDetail.html', {'is_customer': is_customer, 'is_premium_user': str(is_premium_user),'html_table': html_table, 'Groupfilter': Groupfilter, 'IPOTypefilter': IPOTypefilter,'group_names_list':json.dumps(group_names_list),'Panding_Pan_GroupList':json.dumps(Panding_Pan_GroupList), 'InvestorTypeFilter':InvestorTypeFilter, 'IPOName': IPOName, 'Group': Group.order_by('GroupName'), 'IPOid': IPOid, 'AppTotal':AppTotal,'Appwithoutpan':Appwithoutpan,'OrderDate': Od_Date, 'OrderTime': Od_time, 'page_obj': page_obj,'page_size':page_size })
    else:
        return render(request, 'OrderDetail - Sell.html', {'is_customer': is_customer, 'is_premium_user': str(is_premium_user),'html_table': html_table, 'Groupfilter': Groupfilter, 'IPOTypefilter': IPOTypefilter, 'InvestorTypeFilter':InvestorTypeFilter,'group_names_list':json.dumps(group_names_list),'Panding_Pan_GroupList':json.dumps(Panding_Pan_GroupList), 'IPOName': IPOName, 'Group': Group.order_by('GroupName'), 'IPOid': IPOid, 'AppTotal':AppTotal,'Appwithoutpan':Appwithoutpan,'OrderDate': Od_Date, 'OrderTime': Od_time , 'page_obj': page_obj,'page_size':page_size})
    


def resolve_shared_link(request, link_id,order_type=None):
    link = get_object_or_404(SharedLink, id=link_id)
    
    if timezone.now() > link.expiry_at:
        return HttpResponse("<h1>This link has expired.</h1>", status=403)
    if request.method == "POST":
       OrderCategory = request.POST.get('OrderCategory','All')
       InvestorType = request.POST.get('InvestorType','All')
       Rate = request.POST.get('RateFilterValue','All')
    else:
        OrderCategory = 'All'
        InvestorType = 'All'
        Rate = 'All'
           
    
    # 1. Set the guest access flag in session
    request.session[f'access_auth_{link.ipo.id}'] = True
    
    request.session[f'link_owner_{link.ipo.id}'] = link.user.id
    
    request.session['link_expiry'] = (link.expiry_at).isoformat()
    
    request.session[f'access_auth_ipo'] = link.ipo.id
    request.session[f'access'] = str(link_id)
    request.session['group_name'] = link.group.GroupName  # This is what {{ request.session.group_name }} reads
    # 2. Add a flag to tell the template to hide buttons
    request.session['is_guest_view'] = True

    # Call the RENAME function here
    return OrderDetailFunction(
        request, 
        IPOid=str(link.ipo.id), 
        Ordtyp=order_type, 
        GrpName=link.group.GroupName if link.group else "All", 
        OrderCategory=OrderCategory, 
        InvestorType=InvestorType,
        Rate = Rate
    )
    
def get_user_links(request,IPOid,order_type):
    # Filters links created by the current user
    
    links_queryset = SharedLink.objects.filter(
        user=request.user, 
        ipo_id=int(IPOid)
    ).select_related('group', 'ipo') # Optimized to prevent N+1 queries

    # 1. Check for Initial Setup
    if not links_queryset.exists():
        # Check if any orders exist for this IPO to determine if we need a setup prompt
        has_orders = Order.objects.filter(user=request.user, OrderIPOName_id=IPOid, Active=True).exists()
        if has_orders:
            return JsonResponse({'needs_setup': True})
        return JsonResponse({'links': []})

    # 2. Extract current "Master Expiry" from existing links
    # We use the expiry from the most recently created or first available link
    master_link = links_queryset.order_by('id').first()
    master_expiry = master_link.expiry_at if master_link else None
    linked_group_ids = links_queryset.filter(group__isnull=False).values_list('group_id', flat=True)
    
    # 3. Auto-Sync: Identify groups that have orders but no links yet
    missing_groups = GroupDetail.objects.filter(
        user=request.user,
        order__OrderIPOName_id=IPOid,
        order__Active=True
    ).exclude(id__in=linked_group_ids).distinct()

    if missing_groups.exists() and master_expiry:
        ipo_obj = CurrentIpoName.objects.get(id=IPOid)
        for group in missing_groups:
            SharedLink.objects.get_or_create(
                user=request.user,
                ipo=ipo_obj,
                group=group,
                defaults={'expiry_at': master_expiry, 'is_mail_sent': False}
            )
        # Refresh queryset after auto-generation
        links_queryset = SharedLink.objects.filter(
            user=request.user, 
            ipo_id=int(IPOid)
        ).select_related('group', 'ipo').order_by('id')

    links_list = []
    # linked_group_ids = set() # Commented as we handle this via values_list above
    for link in links_queryset:
        # 2. Define the filter for the orders belonging to this link's specific scope
        # If link.group is None, it means "All Groups"
        # if link.group:
        #     linked_group_ids.add(link.group.id)
        
        # group_obj = GroupDetail.objects.filter(
        #     user=request.user, 
        #     GroupName=link.group.GroupName
        # ).first() if link.group else None
        
        entry = OrderDetail.objects.filter(
                user=request.user, Order__OrderIPOName_id=IPOid, Order__OrderGroup=link.group, Order__OrderType=order_type)
    
        AppTotal=len(entry)
        Appwithoutpan=len(entry.filter(OrderDetailPANNo_id=None))
        # 4. Construct the data object for the frontend
        links_list.append({
            'id': link.id,
            'group_id': link.group.id if link.group else None,
            'group__GroupName': link.group.GroupName if link.group else 'All Groups',
            'group__Email': link.group.Email if link.group else 'N/A',
            'ipo__IPOName': link.ipo.IPOName,
            'expiry_at': link.expiry_at,
            'total_pan': AppTotal,
            'pending_pan': Appwithoutpan,
            'is_mail_sent':link.is_mail_sent
        })
        
    # 5. Commented out the manual pending groups loop as they are now auto-generated above
    # pending_groups = GroupDetail.objects.filter(
    #     user=request.user,
    #     order__OrderIPOName_id=IPOid,
    #     order__Active=True
    # ).exclude(id__in=linked_group_ids).distinct()

    # ip_obj = CurrentIpoName.objects.filter(id=IPOid).first()
    # for group in pending_groups:
    #     entry = OrderDetail.objects.filter(...)
    #     ... 
    #     links_list.append({...})

    return JsonResponse({'links': links_list})

@login_required
def delete_link(request, link_id=None):
    if request.method == "POST":
        # Check for bulk IDs in POST
        link_ids_json = request.POST.get('link_ids')
        if link_ids_json:
            try:
                link_ids = json.loads(link_ids_json)
                if not link_ids:
                    return JsonResponse({"status": "failed", "message": "No links selected."}, status=400)
                
                deleted_count, _ = SharedLink.objects.filter(id__in=link_ids, user=request.user).delete()
                return JsonResponse({"status": "success", "message": f"Successfully deleted {deleted_count} link(s)."})
            except Exception as e:
                return JsonResponse({"status": "failed", "message": str(e)}, status=400)

        # Fallback for single ID (though we will use bulk IDs even for 1 link now)
        target_id = link_id or request.POST.get('link_id')
        if target_id:
            link = get_object_or_404(SharedLink, id=target_id, user=request.user)
            link.delete()
            return JsonResponse({"status": "success", "message": "Link deleted successfully."})
            
    return JsonResponse({"status": "failed", "message": "Invalid request."}, status=400)

@login_required
def update_shared_link(request, link_id):
    if request.method == 'POST':
        link = get_object_or_404(SharedLink, id=link_id, user=request.user)
        
        # group_id = request.POST.get('group') # Now disabled in frontend
        expiry_str = request.POST.get('expiry') # Comes as YYYY-MM-DDTHH:MM
        try:
            # 2. Update Expiry (Convert IST back to UTC)
            if expiry_str:
                # Parse the string from the input
                naive_dt = datetime.strptime(expiry_str, '%Y-%m-%dT%H:%M')
                
                # Make it timezone aware
                link.expiry_at = timezone.make_aware(naive_dt)

            link.save()
            return JsonResponse({'status': 'success', 'message': 'Link updated successfully'})
        
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=405)


def send_link_mail(request, linkId):
    if request.method == 'POST':
        try:
            # 1. Fetch the SharedLink and basic info
            link = get_object_or_404(SharedLink, id=linkId, user=request.user)
            request_user = request.user
            ipo_name = link.ipo.IPOName
            
            # 2. Get Group details
            if not link.group:
                return JsonResponse({'status': 'error', 'message': 'This link is not assigned to a group.'}, status=400)
            
            group_name = link.group.GroupName
            GP = GroupDetail.objects.get(GroupName=group_name, user=request_user)
            group_email = GP.Email # Use the email field from your model

            if not group_email:
                return JsonResponse({'status': 'error', 'message': f"Email ID is not available for '{group_name}' Group."}, status=400)

            try:
                validate_email(group_email)
            except ValidationError:
                return JsonResponse({'status': 'error', 'message': f"Invalid email address: {group_email}"}, status=400)

            # 3. CSV Generation
            # Filter entries based on the group and IPO
            entry = OrderDetail.objects.filter(
                user=request_user, 
                Order__OrderIPOName=link.ipo, 
                Order__OrderGroup_id=GP.id, 
                Order__OrderType='BUY'
            )

            csv_buffer = StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(['Group', 'IPO Type', 'Investor Type', 'Rate', 'PAN No',
                             'Client Name', 'AllotedQty', 'Demat Number', 'Application Number', 'Order Date', 'Order Time'])

            # Assuming the link is for "Pending PAN" as per your previous logic
            rows = entry.filter(OrderDetailPANNo_id=None)

            for member in rows.values_list('Order__OrderGroup__GroupName', 'Order__OrderCategory', 'Order__InvestorType',
                                           'Order__Rate', 'OrderDetailPANNo__PANNo', 'OrderDetailPANNo__Name', 'AllotedQty',
                                           'DematNumber', 'ApplicationNumber', 'Order__OrderDate', 'Order__OrderTime'):
                List = list(member)
                # Format Date
                if List[9]:
                    List[9] = List[9].strftime('%d/%m/%Y')
                # Format Demat Number for Excel
                if List[7]:
                    List[7] = "'" + str(List[7])
                writer.writerow(tuple(List))

            csv_content = csv_buffer.getvalue()

            # 4. Construct Email
            # Replace these with your actual email settings or request data
            user_email = request.user.email 
            user_app_pw = request.user.AppPassword
            
            full_url = f"{request.scheme}://{request.get_host()}/access-link/{link.id}/BUY"

            msg = MIMEMultipart()
            msg['Subject'] = 'Update Required – Missing Details in Attached File'
            msg['From'] = user_email
            msg['To'] = group_email

            body = f"""\
Dear {group_name},

Please find the attached document which requires your input. We kindly ask you to provide the following missing information:

• PAN Number (Mandatory)
• Name (Optional)
• Client ID (Optional)
• DP ID (Optional)
• Application Number (Optional)

Alternatively, you can update these details directly via our secure portal here:
{full_url}

Regards,
{request_user.username}
"""
            msg.attach(MIMEText(body, 'plain'))

            # Attach CSV
            # part = MIMEApplication(csv_content, Name=f'{group_name}_{ipo_name}.csv')
            # part['Content-Disposition'] = f'attachment; filename="{group_name}_{ipo_name}.csv"'
            # msg.attach(part)

            # 5. Send via SMTP
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(user_email, user_app_pw)
                smtp.send_message(msg)

            # 6. Update Link Status
            link.is_mail_sent = True
            link.save()

            return JsonResponse({'status': 'success', 'message': f'Mail sent successfully to {group_email}!'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=405)

def update_all_expiries(request, IPOid):
    if request.method == 'POST':
        expiry_at = request.POST.get('expiry_at')
        link_ids_json = request.POST.get('link_ids', '[]')
        
        try:
            link_ids = json.loads(link_ids_json)
        except json.JSONDecodeError:
            link_ids = []

        if expiry_at and link_ids:
            # Update specific SharedLinks for this IPO created by the user
            updated_count = SharedLink.objects.filter(
                id__in=link_ids,
                user=request.user, 
                ipo_id=IPOid
            ).update(
                expiry_at=parse_datetime(expiry_at)
            )
            return JsonResponse({'status': 'success', 'message': f'Expiry updated for {updated_count} selected group(s).'})
        elif not link_ids:
            return JsonResponse({'status': 'error', 'message': 'No groups selected for update.'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'}, status=400)

# 2. Send all mails for this IPO
def send_all_link_mails(request, IPOid):
    if request.method == 'POST':
        # Check sender's configuration
        if not request.user.email or not request.user.AppPassword:
            return JsonResponse({'status': 'error', 'message': 'Please configure your Email and App Password in your profile first.'})

        selected_links_json = request.POST.get('selected_links', '[]')
        try:
            selected_links = json.loads(selected_links_json)
        except json.JSONDecodeError:
            selected_links = []

        # Get links for this IPO that have a group assigned
        base_query = SharedLink.objects.filter(user=request.user, ipo_id=IPOid).exclude(group=None)
        
        if selected_links and 'all' not in selected_links:
            links = base_query.filter(id__in=selected_links)
        else:
            links = base_query
            
        if not links.exists():
            return JsonResponse({'status': 'error', 'message': 'No valid links found for the selection.'})
        
        successful_links = []
        failed_groups = []
        tasks = []

        for link in links:
            group_obj = link.group
            if not group_obj.Email:
                failed_groups.append(f"{group_obj.GroupName} (No Email Entered)")
                continue

            try:
                # Prepare async tasks
                expiry_date = link.expiry_at
                coro = create_ipo_link(request, request.user, IPOid, group_obj, expiry_date, send_email=True, link_genrate=False)
                tasks.append(coro)
                # Count as queued for success since SMTP is offloaded asynchronously
                successful_links.append(str(link.id))
            except Exception as e:
                traceback.print_exc()
                failed_groups.append(f"{group_obj.GroupName} (Error queueing mail)")
                continue

        if tasks:
            async def run_tasks(tasks_list):
                await asyncio.gather(*tasks_list)
            async_to_sync(run_tasks)(tasks)
                
        if not successful_links and failed_groups:
            return JsonResponse({
                'status': 'error', 
                'message': 'Failed to send targeted mails.',
                'errors': failed_groups
            })

        return JsonResponse({
            'status': 'success', 
            'successful_links': successful_links,
            'failed_groups': failed_groups
        })

# Helper Function: Reusable Link Logic
async def create_ipo_link(request,user, ipo_id, group_obj, expiry_str, send_email=False,link_genrate=False):
    # Create the link
    if link_genrate:
        expiry_date = parse_datetime(expiry_str) if expiry_str else (timezone.now() + timezone.timedelta(days=1))
        link, created = await sync_to_async(SharedLink.objects.update_or_create)(
            user=user,
            ipo_id=ipo_id,
            group=group_obj,
            defaults={'expiry_at': expiry_date, 'is_mail_sent': False}
        )
    else:
        link = await sync_to_async(lambda: SharedLink.objects.filter(user=user, ipo_id=ipo_id, group=group_obj).first())()
    
    full_url = f"{request.scheme}://{request.get_host()}/access-link/{link.id}/BUY"
    
    if send_email and group_obj.Email: # Assuming GroupDetail has an Email field
        try:
            user_email = request.user.email 
            user_app_pw = request.user.AppPassword
            
            msg = MIMEMultipart()
            msg['Subject'] = 'Update Required – Missing Details in Attached File'
            msg['From'] = user_email
            msg['To'] = group_obj.Email
            body = f"""\
    Dear {group_obj.GroupName},

    Please find the attached document which requires your input. We kindly ask you to provide the following missing information:

    • PAN Number (Mandatory)
    • Name (Optional)
    • Client ID (Optional)
    • DP ID (Optional)
    • Application Number (Optional)

    Alternatively, you can update these details directly via our secure portal here:
    {full_url}

    Regards,
    {request.user.username}
"""
            msg.attach(MIMEText(body, 'plain'))

            # 5. Send via SMTP
            await aiosmtplib.send(
                msg,
                hostname="smtp.gmail.com",
                port=465,
                username=user_email,
                password=user_app_pw,
                use_tls=True
            )
            link.is_mail_sent = True
            await sync_to_async(link.save)()
        except Exception as e:
            print(f"Mail Error: {e}")
            
    return link

# The View for the Popup
def bulk_generate_links(request, IPOid):
    if request.method == "POST":
        try:
            expiry_date = request.POST.get('expiry_date')
            action_type = request.POST.get('action_type') # 'generate' or 'generate_send'
            
            selected_groups_json = request.POST.get('selected_groups', '[]')
            selected_groups = json.loads(selected_groups_json)
            
            if 'all' in selected_groups:
                try:
                    target_id = int(IPOid)
                except:
                    target_id = IPOid
                # Get all groups that have orders in this IPO
                group_ids = Order.objects.filter(
                    user=request.user,
                    OrderIPOName_id=target_id,
                    Active=True
                ).values_list('OrderGroup', flat=True).distinct()
                groups = GroupDetail.objects.filter(user=request.user, id__in=group_ids)
            else:
                groups = GroupDetail.objects.filter(user=request.user, id__in=selected_groups)

            if not groups.exists():
                return JsonResponse({'status': 'error', 'message': 'No groups found for selection.'})
            
            for group in groups:
                should_mail = (action_type == 'generate_send')
                # Run creation synchronously for each group to avoid complex async issues in setup
                async_to_sync(create_ipo_link)(
                    request, 
                    request.user, 
                    IPOid, 
                    group, 
                    expiry_date, 
                    send_email=should_mail,
                    link_genrate=True
                )
            
            return JsonResponse({
                'status': 'success', 
                'message': f'Processed {groups.count()} groups successfully!'
            })
        except Exception as e:
            traceback.print_exc()
            return JsonResponse({
                'status': 'error', 
                'message': f"Server Error: {str(e)}"
            }, status=500)
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=400)

def update_link_status(request):
    if request.method == 'POST':
        link_id = request.POST.get('link_id')
        new_status = request.POST.get('status') # 'Sent' or 'Pending'
        
        try:
            # Fetch the link belonging to the current user
            link = get_object_or_404(SharedLink, id=link_id, user=request.user)
            
            # Map the string status back to your boolean field
            if new_status == 'Sent':
                link.is_mail_sent = True
            else:
                link.is_mail_sent = False
            
            link.save()
            
            return JsonResponse({
                'status': 'success', 
                'message': f'Status updated to {new_status}'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error', 
                'message': str(e)
            }, status=400)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)
