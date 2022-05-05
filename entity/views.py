
from __future__ import print_function
from django.shortcuts import render, redirect, HttpResponse
from account.models import Account
from account.forms import AccountForm,LoginForm
from django.conf import settings
from django.http import JsonResponse
import os
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
import io
import sys
import hashlib

SCOPES = ['https://www.googleapis.com/auth/drive']

def index(request):
    if 'id' in request.session:
        return render(request,'home.html')    
    return render(request,'index.html')

def signin(request):
    account_form = AccountForm(request.POST or None)
    if account_form.is_valid():
        obj = account_form.save()
        request.session['id'] = obj.id
        request.session['user'] = obj.userName
        return redirect(f"/oauth/{obj.userName}")
    context = {'account_form': account_form}
    return render(request, 'signin.html', context)  

def login(request):
    account_form = LoginForm(request.POST or None)
    if account_form.is_valid():
        obj = account_form.save(commit=False)
        accountSet = Account.objects.filter(email=obj.email,password=obj.password)
        if accountSet.count != 0:
            request.session['id'] = accountSet[0].id 
            request.session['user'] = accountSet[0].userName
            #return redirect(f"")
            return redirect("/")

    context = {'account_form': account_form}
    return render(request, 'login.html', context)

def oauth(request,user):
    creds = None
    my_path = settings.BASE_DIR / 'tokens' / f'{user}.json'
    if my_path.exists():
        creds = Credentials.from_authorized_user_file(f'{user}.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(my_path, 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('drive', 'v3', credentials=creds)

        # Call the Drive v3 API
        results = service.files().list(
            pageSize=10, fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])
        if not items:
            print('No files found.')
            return
        print('Files:')
        for item in items:
            print(u'{0} ({1})'.format(item['name'], item['id']))
    except HttpError as error:
        # TODO(developer) - Handle errors from drive API.
        print(f'An error occurred: {error}')
        return HttpResponse('all good exept')
    finally:
        return redirect("/")

def updateInfo(request):
    if 'id' in request.session:
        userinfo = ""
        emailinfo = ""
        passwordinfo = ""
        account = Account.objects.get(id=request.session['id'])
        oldName = settings.BASE_DIR / 'tokens' / f'{account.userName}.json'
        if request.method == 'POST':
            data = request.POST.copy()
            if data.get('username') != account.userName:
                accounts = Account.objects.filter(userName=data.get('username'))
                if accounts.count() == 0:
                    account.userName = data.get('username')
                    newName = settings.BASE_DIR / 'tokens' / f'{data.get("username")}.json'
                    os.rename(oldName, newName)
                    request.session['user'] = account.userName
                else:
                    userinfo = "userName already exists"
            if data.get('email') != account.email:
                accounts = Account.objects.filter(email=data.get('email'))
                if accounts.count() == 0:
                    account.email = data.get('email')
                else:
                    emailinfo = "email already exists"
            if data.get('password') != account.password:
                account.userName = data.get('password')

            account.save()
            return redirect("/")
        context = {'account_form': account,"username":userinfo,"email":emailinfo,"password":passwordinfo}
        return render(request, 'updateinfo.html', context) 


def updateDrive(request):
    if 'id' in request.session:
        username = request.session['user']
        my_path = settings.BASE_DIR / 'tokens' / f'{username}.json'
        os.remove(my_path)
        return redirect(f"/oauth/{username}")
    return redirect("/")

def logout(request):
    del request.session['id']
    return redirect("/")

#----------------------------------------------------------------------------------------------------------
#api views part:

def connect(request):
    #http://localhost:8000/api/connect/?username={}&password={}
    res = {}
    if request.method == "GET":
        data = request.GET.copy()
        username = data.get("username")
        password = data.get("password")
        accounts = Account.objects.filter(userName=username,password=password)
        if accounts.count() != 0:
            res['status'] = "yes"
            res['id'] = accounts[0].id
        else:
            res['status'] = "no"
            res['id'] = -1
    return JsonResponse(res)

def checkSecurity(request):
    #http://localhost:8000/api/check/?id={}&filehash={}&filename={}
    res = {}
    if request.method == "GET":
        try:
            data = request.GET.copy()
            userId = data.get("id")
            fileHash = data.get("filehash")
            fileName = data.get("filename")
            accounts = Account.objects.get(id=int(userId))
            creds = None
            my_path = settings.BASE_DIR / 'tokens' / f'{accounts.userName}.json'
            if my_path.exists():
                creds = Credentials.from_authorized_user_file(f'{my_path}', SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'client_secret.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                #  Save the credentials for the next run
                with open(my_path, 'w') as token:
                    token.write(creds.to_json())
            
            service = build('drive', 'v3', credentials=creds)
        # Call the Drive v3 API
            results = service.files().list(
                pageSize=10, fields="nextPageToken, files(id, name)").execute()
            items = results.get('files', [])
            if not items:
                print('No files found.')
                return
            file_id = ""
            exists = False
            print('Files:')
            for item in items:
                print(u'{0} ({1})'.format(item['name'], item['id']))
                if item['name'] == fileName:
                    print("insde the if statment .................")
                    file_id = item['id']
                    exists = True
                    break

            if not exists:
                res['message'] = "file not found."
            request = service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print(f"Download {int(status.progress() * 100)}%")
            print(f"file content : {fileHash} ")
            encoded_str = str(fh.getvalue()).encode()
            obj_sha3_256 = hashlib.sha3_256(fh.getvalue())
            if obj_sha3_256.hexdigest() == fileHash:
                print("the file is the same.............")
                res['status'] = "yes"
                res['message'] = "no security issuas found. file is the same."
            else:
                print("file hash is not the same ........")
                res['status'] = "no"
                res['message'] = "security breach found, file has been changed"
                    
        except:
            res['status'] = "no"
            res['message'] = "server error"
        finally:
            return JsonResponse(res)


def checkSecurity2(request):
    #http://localhost:8000/api/check/?id={}&filehash={}&filename={}
    res = {}
    if request.method == "GET":
        try:
            data = request.GET.copy()
            userId = data.get("id")
            fileHash = data.get("filehash")
            fileName = data.get("filename")
            accounts = Account.objects.get(id=int(userId))
            creds = None
            my_path = settings.BASE_DIR / 'tokens' / f'{accounts.userName}.json'
            if my_path.exists():
                creds = Credentials.from_authorized_user_file(f'{my_path}', SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'client_secret.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                #  Save the credentials for the next run
                with open(my_path, 'w') as token:
                    token.write(creds.to_json())
            
            service = build('drive', 'v3', credentials=creds)
        # Call the Drive v3 API
            results = service.files().list(
                pageSize=10, fields="nextPageToken, files(id, name)").execute()
            items = results.get('files', [])
            if not items:
                print('No files found.')
                return
            print('Files:')
            for item in items:
                print(u'{0} ({1})'.format(item['name'], item['id']))
                if item['name'] == fileName:
                    print("insde the if statment .................")
                    file_id = item['id']
                    request = service.files().get_media(fileId=file_id)
                    fh = io.BytesIO()
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()
                        print(f"Download {int(status.progress() * 100)}%")
                    print(f"file content : {fileHash} ")
                    encoded_str = str(fh.getvalue()).encode()
                    print(f"fh.getvalue : {fh.getvalue()}")
                    print(f"encoded_str : {encoded_str}")
                    print(f"bytes : {fh.read()}")
                    obj_sha3_256 = hashlib.sha3_256(fh.getvalue())
                    print(f"SHA3-256 Hash: {obj_sha3_256.hexdigest()}")
                    print(f"file hash is : {fileHash}")
                    if obj_sha3_256.hexdigest() == fileHash:
                        print("the file is the same.............")
                    else:
                        print("file hase been changed.........")
                    
                    res['status'] = "yes"
        except:
            res['status'] = "no"
        finally:
            return JsonResponse(res)

def saveEccPart(request):
    #http://localhost:8000/api/saveeccpart/?id={}&partn={}&part={}
    res = {}
    if request.method == "GET":
        data = request.GET.copy()
        userId = data.get("id")
        part = data.get("part")
        partNumber = data.get("partn")
        try:
            accounts = Account.objects.get(id=int(userId))
            if int(partNumber) == 1 :
                accounts.eccPart1 = part
                res['status'] = "yes"
            if int(partNumber) == 2 :
                accounts.eccPart2 = part
                res['status'] = "yes"
            if int(partNumber) == 3 :
                accounts.eccPart3 = part
                res['status'] = "yes"
            if int(partNumber) == 4 :
                accounts.eccPart4 = part
                res['status'] = "yes"
            accounts.save()
        except:
            res['status'] = "no"
    return JsonResponse(res)

def getEccPart(request):
    #http://localhost:8000/api/geteccpart/?id={}&partn={}
    res = {}
    if request.method == "GET":
        data = request.GET.copy()
        userId = data.get("id")
        partNumber = data.get("partn")
        try:
            accounts = Account.objects.get(id=int(userId))
            if int(partNumber) == 1 :
                res['status'] = "yes"
                res['part'] = accounts.eccPart1
            if int(partNumber) == 2 :
                res['status'] = "yes"
                res['part'] = accounts.eccPart2
            if int(partNumber) == 3 :
                res['status'] = "yes"
                res['part'] = accounts.eccPart3
            if int(partNumber) == 4 :
                res['status'] = "yes"
                res['part'] = accounts.eccPart4
        except:
            res['status'] = "no"
            res['part'] = ""
    return JsonResponse(res)