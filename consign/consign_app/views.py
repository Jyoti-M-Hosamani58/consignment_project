from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, reverse, redirect, get_object_or_404

from consign_app.models import Login, AddConsignment,AddConsignmentTemp, AddTrack,FeedBack, Branch, Driver, Staff,Consignee, Consignor,TripSheetTemp,TripSheetPrem, Account,Expenses
#from django.core.mail import send_mail

import datetime
import random
import string
import secrets

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from django.conf import settings
from django.core.files.storage import FileSystemStorage
import os
from consign.settings import BASE_DIR
from django.db.models import Q, Max
from django.contrib import messages
from django.utils import timezone

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
import json
from django.views.decorators.http import require_POST
from django.db.models import Count
from django.core.exceptions import ValidationError
from datetime import datetime
from decimal import Decimal
from django.core.exceptions import ValidationError

from django.db.models.functions import Concat
from django.db import connection, IntegrityError
from collections import defaultdict



from .models import Location  # Assume you have a Location model

#import datetime
#from .models import AddTrack, AddConsignment




# Create your views here.
def index(request):
    return render(request,'index.html')



def feedback(request):
    uid = request.session.get('username')
    if not uid:
        return redirect('login')  # Redirect to login if session does not have username

    # Fetch only the receiver_email column
    userdata = AddConsignment.objects.filter(receiver_email=uid).values_list('receiver_email', flat=True)

    if request.method == "POST":
        feed = request.POST.get('feedback')

        if userdata.exists():
            username = userdata[0]  # Extract the first email from the list

            FeedBack.objects.create(
                username=username,
                feedback=feed
            )
            messages.success(request, 'Feedback sent successfully')
            return redirect('feedback')
        else:
            messages.error(request, 'User not found')
            return render(request, 'feedback.html')

    return render(request, 'feedback.html')

def view_feedback(request):
    userdata=FeedBack.objects.all()
    return render(request,'view_feedback.html',{'userdata':userdata})

def staff_home(request):
    return render(request,'staff_home.html')

def staff_nav(request):
    return render(request,'staff_nav.html')

def index_menu(request):
    return render(request,'index_menu.html')

def admin_home(request):
    return render(request,'admin_home.html')

def user_home(request):
    return render(request,'user_home.html')

def user_home(request):
    return render(request,'user_home.html')

def user_menu(request):
    return render(request,'user_menu.html')

def nav(request):
    return render(request,'nav.html')


def userlogin(request):
    if request.method=="POST":
        username=request.POST.get('t1')
        password=request.POST.get('t2')
        request.session['username']=username
        ucount=Login.objects.filter(username=username).count()
        if ucount>=1:
            udata = Login.objects.get(username=username)
            upass = udata.password
            utype=udata.utype
            if password == upass:
                request.session['utype'] = utype
                if utype == 'user':
                    return render(request,'user_home.html')
                if utype == 'admin':
                    return render(request,'admin_home.html')
                if utype == 'branch':
                    return render(request,'branch_home.html')
                if utype == 'staff':
                    return render(request,'staff_home.html')
            else:
                return render(request,'userlogin.html',{'msg':'Invalid Password'})
        else:
            return render(request,'userlogin.html',{'msg':'Invalid Username'})
    return render(request,'userlogin.html')


def addConsignment(request):
    if request.method == "POST":
        now = datetime.now()
        con_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")

        # Get the last track_id and increment it
        last_track_id = AddConsignment.objects.aggregate(Max('track_id'))['track_id__max']
        track_id = int(last_track_id) + 1 if last_track_id else 1000
        con_id = str(track_id)

        # Get the last Consignment_id and increment it
        last_con_id = AddConsignment.objects.aggregate(Max('Consignment_id'))['Consignment_id__max']
        Consignment_id = last_con_id + 1 if last_con_id else 1000
        Consignment_id = str(Consignment_id)

        # Sender details
        send_name = request.POST.get('a1')
        send_mobile = request.POST.get('a2')
        send_email = request.POST.get('a3')
        send_address = request.POST.get('a4')
        sender_GST = request.POST.get('sendergst')
        sender_company = request.POST.get('sen_company')

        # Receiver details
        rec_name = request.POST.get('a5')
        rec_mobile = request.POST.get('a6')
        rec_email = request.POST.get('a7')
        rec_address = request.POST.get('a8')
        rec_GST = request.POST.get('receivergst')
        rec_company = request.POST.get('receiverCompany')

        # Copy types
        copies = []
        if request.POST.get('consignor_copy'):
            copies.append('Consignor Copy')
        if request.POST.get('consignee_copy'):
            copies.append('Consignee Copy')
        if request.POST.get('lorry_copy'):
            copies.append('Lorry Copy')
        copy_type = ', '.join(copies)

        # Create or update Consignor
        consignor, created = Consignor.objects.update_or_create(
            sender_email=send_email,
            defaults={
                'sender_name': send_name,
                'sender_mobile': send_mobile,
                'sender_address': send_address,
                'sender_GST': sender_GST,
                'sender_company': sender_company
            }
        )

        # Create or update Consignee
        consignee, created = Consignee.objects.update_or_create(
            receiver_email=rec_email,
            defaults={
                'receiver_name': rec_name,
                'receiver_mobile': rec_mobile,
                'receiver_address': rec_address,
                'receiver_GST': rec_GST,
                'receiver_company': rec_company
            }
        )

        # Handling product entries
        products = request.POST.getlist('product[]')
        pieces = request.POST.getlist('pieces[]')

        # Other consignment details
        prod_invoice = request.POST.get('prod_invoice')
        prod_price = request.POST.get('prod_price')

        weight = float(request.POST.get('weight'))
        freight = float(request.POST.get('freight'))
        hamali = float(request.POST.get('hamali'))
        door_charge = float(request.POST.get('door_charge'))
        st_charge = float(request.POST.get('st_charge'))

        # Calculate total cost
        total_cost = freight + hamali + door_charge + st_charge

        route_from = request.POST.get('from')
        route_to = request.POST.get('to')
        cost = float(request.POST.get('cost'))

        pay_status = request.POST.get('payment')

        uid = request.session.get('username')
        branch = Staff.objects.get(staffPhone=uid)
        branchname=branch.Branch
        uname = branch.staffname

        utype = request.session.get('utype')
        branch_value = 'admin' if utype == 'admin' else uname

        # Loop through products and save each one
        for product, piece in zip(products, pieces):
            if not product or not piece:
                continue
            AddConsignment.objects.create(
                track_id=con_id,
                Consignment_id=Consignment_id,
                sender_name=send_name,
                sender_mobile=send_mobile,
                sender_email=send_email,
                sender_address=send_address,
                sender_GST=sender_GST,
                sender_company=sender_company,
                receiver_name=rec_name,
                receiver_mobile=rec_mobile,
                receiver_email=rec_email,
                receiver_address=rec_address,
                receiver_GST=rec_GST,
                receiver_company=rec_company,
                desc_product=product,
                pieces=piece,
                prod_invoice=prod_invoice,
                prod_price=prod_price,
                weight=weight,
                freight=freight,
                hamali=hamali,
                door_charge=door_charge,
                st_charge=st_charge,
                route_from=route_from,
                route_to=route_to,
                total_cost=cost,
                date=con_date,
                pay_status=pay_status,
                branch=branchname,
                name=uname,
                time=current_time,
                copy_type=copy_type
            )

        # Also create records in AddConsignmentTemp for temporary storage
        for product, piece in zip(products, pieces):
            if not product or not piece:
                continue

            AddConsignmentTemp.objects.create(
                track_id=con_id,
                Consignment_id=Consignment_id,
                sender_name=send_name,
                sender_mobile=send_mobile,
                sender_email=send_email,
                sender_address=send_address,
                sender_GST=sender_GST,
                sender_company=sender_company,
                receiver_name=rec_name,
                receiver_mobile=rec_mobile,
                receiver_email=rec_email,
                receiver_address=rec_address,
                receiver_GST=rec_GST,
                receiver_company=rec_company,
                desc_product=product,
                pieces=piece,
                prod_invoice=prod_invoice,
                prod_price=prod_price,
                weight=weight,
                freight=freight,
                hamali=hamali,
                door_charge=door_charge,
                st_charge=st_charge,
                route_from=route_from,
                route_to=route_to,
                total_cost=cost,
                date=con_date,
                pay_status=pay_status,
                branch=branchname,
                name=uname,
                time=current_time,
                copy_type=copy_type
            )
            # Fetch previous balance entry
            previous_balance_entry = Account.objects.filter(sender_name=send_name, track_number=con_id).order_by(
                '-Date').first()
            if previous_balance_entry:
                previous_balance = float(previous_balance_entry.Balance)
            else:
                previous_balance = 0.0  # Initialize balance to 0 if no previous entries

            # Update the current balance for the sender
            updated_balance = previous_balance + cost

            try:
                # Create the Account model entry
                Account.objects.create(
                    Date=now,  # Use current date and time
                    track_number=con_id,
                    debit="0",
                    credit=str(cost),
                    TrType="sal",
                    particulars=f"{con_id} Debited",  # Use f-string for dynamic insertion
                    Balance=str(updated_balance),
                    sender_name=send_name,
                    headname=uname,  # Save the headname in the Account model as well
                )
                return JsonResponse({'status': 'success'})
            except IntegrityError:
                return JsonResponse({'status': 'error', 'message': 'Entry with this track number already exists'})

        # Generate a random password
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for i in range(8))

        # Check if the user already exists
        user, created = Login.objects.update_or_create(
            username=rec_email,
            defaults={
                'password': password,  # Store the password directly
                'utype': 'user'
            }
        )

        if created:
            print("New user created with password:", password)
        else:
            print("User already exists. Updated password to:", password)

        return redirect('printConsignment', track_id=con_id)

    else:
        # Fetch the vehicle numbers from the Driver model
        vehicle_numbers = Driver.objects.values_list('vehicle_number', flat=True)

        # Pass vehicle numbers to the template
        return render(request, 'addConsignment.html', {'vehicle_numbers': vehicle_numbers})




def printConsignment(request, track_id):
    # Filter consignments by track_id
    consignments = AddConsignment.objects.filter(track_id=track_id)
    uid = request.session.get('username')
    branch = Staff.objects.get(staffPhone=uid)
    branchname=branch.Branch
    branchdetails=Branch.objects.get(companyname=branchname)

    if not consignments.exists():
        return render(request, '404.html')  # Handle the case where no consignments are found.

    # Get common details from the first consignment
    consignment = consignments.first()

    # Collect copy_types from all consignments with the same track_id
    copy_types = consignments.values_list('copy_type', flat=True).distinct()

    # Convert the queryset to a list and join them into a single string for display
    copy_type_list = ', '.join(copy_types)

    # Pass the first consignment, the entire list of items, and the copy types to the template
    return render(request, 'printConsignment.html', {
        'consignment': consignment,
        'items': consignments,
        'branchdetails': branchdetails,
        'copy_types': copy_type_list  # Include the aggregated copy types
    })

def invoiceConsignment(request, pk):
    consignment = get_object_or_404(AddConsignment, id=pk)
    branch = consignment.branch
    branchdetails = get_object_or_404(Branch, companyname=branch)
    return render(request, 'invoiceConsignment.html', {'consignment': consignment,'branchdetails':branchdetails})

def view_consignment(request):
    uid = request.session.get('username')
    userdata = AddConsignment.objects.none()

    if uid:
        try:
            branch = Staff.objects.get(staffPhone=uid)
            user_branch = branch.Branch  # Adjust if the branch info is stored differently

            userdata = AddConsignment.objects.filter(branch=user_branch)

        except ObjectDoesNotExist:
            userdata = AddConsignment.objects.none()

    return render(request,'view_consignment.html',{'userdata':userdata})

def user_view_consignment(request):
    uid = request.session['username']
    userdata = AddConsignment.objects.filter(receiver_email=uid).values()
    return render(request,'user_view_consignment.html',{'userdata':userdata})


def consignment_edit(request, pk):
    userdata = AddConsignment.objects.filter(id=pk).first()  # Retrieve a single object or None


    if request.method == "POST":
        track_id = userdata.track_id
        con_date = userdata.date

        send_name = request.POST.get('a1')
        send_mobile = request.POST.get('a2')
        send_email = request.POST.get('a3')
        send_address = request.POST.get('a4')

        rec_name = request.POST.get('a5')
        rec_mobile = request.POST.get('a6')
        rec_email = request.POST.get('a7')
        rec_address = request.POST.get('a8')

        cost = request.POST.get('a9')

        # Update the object
        userdata.track_no = track_id
        userdata.sender_name = send_name
        userdata.sender_mobile = send_mobile
        userdata.sender_email = send_email
        userdata.sender_address = send_address
        userdata.receiver_name = rec_name
        userdata.receiver_mobile = rec_mobile
        userdata.receiver_email = rec_email
        userdata.receiver_address = rec_address
        userdata.total_cost = cost
        userdata.date = con_date
        userdata.save()

        # Redirect to a different URL after successful update
        base_url = reverse('view_consignment')
        return redirect(base_url)

    return render(request, 'consignment_edit.html', {'userdata': userdata})


def consignment_delete(request,pk):
    udata=AddConsignment.objects.get(id=pk)
    udata.delete()
    base_url=reverse('view_consignment')
    return redirect(base_url)




def addTrack(request):
    consignments = AddConsignment.objects.all().order_by('-id')  # Fetch all consignments ordered by id descending
    if request.method == "POST":
        now = datetime.datetime.now()
        con_date = now.strftime("%Y-%m-%d")

        track_id = request.POST.get('a1')
        status = request.POST.get('status')  # Retrieve status from the form

        # Retrieve total_cost from AddConsignment table based on some condition
        # For example, you can get it based on track_id or any other criteria

        # If the selected status is "Other", retrieve the custom status from the form
        if status == "Other":
            custom_status = request.POST.get('a2')
        else:
            custom_status = None

        # Create AddTrack object with retrieved total_cost
        AddTrack.objects.create(
            track_id=track_id,
            description=status,
            date=con_date

        )

        return render(request, 'addTrack.html', {'msg': 'Added'})
    return render(request, 'addTrack.html',{'consignments':consignments})


def search_results(request):
    tracker_id = request.GET.get('tracker_id')
    consignments = AddConsignment.objects.all().order_by('-id')  # Fetch all consignment data

    if tracker_id:
        try:
            trackers = AddTrack.objects.filter(track_id=tracker_id)
            if trackers.exists():
                return render(request, 'search_results.html', {'trackers': trackers, 'consignments': consignments})
            else:
                message = f"No tracking information found for ID: {tracker_id}"
                return render(request, 'search_results.html', {'message': message, 'consignments': consignments})
        except Exception as e:
            message = f"Error occurred: {str(e)}"
            return render(request, 'search_results.html', {'message': message, 'consignments': consignments})
    else:
        return render(request, 'search_results.html', {'message': "Please enter a tracker ID.", 'consignments': consignments})



def track_delete(request,pk):
    udata=AddTrack.objects.get(id=pk)
    udata.delete()
    base_url=reverse('search_results')
    return redirect(base_url)


def user_search_results(request):
    tracker_id = request.GET.get('tracker_id')

    if tracker_id:
        try:
            trackers = AddTrack.objects.filter(track_id=tracker_id)
            if trackers.exists():
                return render(request, 'user_search_results.html', {'trackers': trackers})
            else:
                message = f"No tracking information found for ID: {tracker_id}"
                return render(request, 'user_search_results.html', {'message': message})
        except Exception as e:
            message = f"Error occurred: {str(e)}"
            return render(request, 'user_search_results.html', {'message': message})
    else:
        return render(request, 'user_search_results.html', {'message': "Please enter a tracker ID."})






def branch(request):
    if request.method == "POST" and request.FILES['image']:

        companyname = request.POST.get('companyname')
        headname = request.POST.get('headname')
        phonenumber = request.POST.get('phonenumber')
        email = request.POST.get('email')
        password=request.POST.get('password')
        gst = request.POST.get('gst')
        address = request.POST.get('address')
        image = request.POST.get('image')

        utype = 'branch'
        myfile = request.FILES['image']
        fs = FileSystemStorage()
        filename = fs.save(myfile.name, myfile)
        upload_file_url = fs.url(filename)
        path = os.path.join(BASE_DIR, '/media/' + filename)


        Branch.objects.create(
            companyname=companyname,
            phonenumber=phonenumber,
            email=email,
            gst=gst,
            address=address,
            image=myfile,
            headname=headname,
            password=password

        )
        Login.objects.create(utype=utype, username=email, password=password,name=headname)

    return render(request, 'branch.html')



def view_branch(request):
    data=Branch.objects.all()
    return render(request,'view_branch.html',{'data':data})


def edit_branch(request, pk):
    data = Branch.objects.filter(id=pk).first()  # Retrieve a single object or None

    original_email = data.email

    if request.method == "POST":
        companyname = request.POST.get('companyname')
        headname = request.POST.get('headname')
        phonenumber = request.POST.get('phonenumber')
        email = request.POST.get('email')
        gst = request.POST.get('gst')
        address = request.POST.get('address')
        password = request.POST.get('password')

        # Update the object
        data.companyname = companyname
        data.headname = headname
        data.phonenumber = phonenumber
        data.email = email
        data.gst = gst
        data.address = address
        data.password=password
        data.save()


        # Update the Login record using the original staffPhone
        user = Login.objects.filter(username=original_email).first()  # Fetch the user with the original phone number
        if user:
            user.username = email  # Update username to the new phone number
            user.name = headname  # Update name
            user.password=password
            user.save()
        # Redirect to a different URL after successful update
        base_url = reverse('view_branch')
        return redirect(base_url)

    return render(request, 'edit_branch.html', {'data': data})

def branch_delete(request,pk):
    udata=Branch.objects.get(id=pk)
    user = Login.objects.filter(username=udata.email).first()
    if user:
        user.delete()
    udata.delete()
    base_url=reverse('view_branch')
    return redirect(base_url)

def driver(request):
    if request.method == "POST":
        driver_name = request.POST.get('driver_name')
        phone_number = request.POST.get('phone_number')
        address = request.POST.get('address')
        vehicle_number=request.POST.get('vehicle_number')

        Driver.objects.create(
            driver_name=driver_name,
            phone_number=phone_number,
            address=address,
            vehicle_number=vehicle_number,


        )


    return render(request, 'driver.html')


def view_driver(request):
    data=Driver.objects.all()
    return render(request,'view_driver.html',{'data':data})


def driver_edit(request, pk):
    data = Driver.objects.filter(id=pk).first()  # Retrieve a single object or None


    if request.method == "POST":
        driver_name = request.POST.get('driver_name')
        phone_number = request.POST.get('phone_number')
        address = request.POST.get('address')
        vehicle_number = request.POST.get('vehicle_number')


        # Update the object
        data.driver_name = driver_name
        data.phone_number = phone_number
        data.address = address
        data.vehicle_number = vehicle_number

        data.save()

        # Redirect to a different URL after successful update
        base_url = reverse('view_driver')
        return redirect(base_url)

    return render(request, 'driver_edit.html', {'data': data})


def driver_delete(request,pk):
    udata=Driver.objects.get(id=pk)
    udata.delete()
    base_url=reverse('view_driver')
    return redirect(base_url)


def get_consignor_name(request):
    query = request.GET.get('query', '')
    if query:
        sender_names = Consignor.objects.filter(sender_name__icontains=query).values_list('sender_name', flat=True)
        print('sender_names numbers:', list(sender_names))  # Debugging: check the data in the terminal
        return JsonResponse(list(sender_names), safe=False)
    return JsonResponse([], safe=False)

def get_sender_details(request):
    name = request.GET.get('name', '')
    if name:
        consignor = Consignor.objects.filter(sender_name=name).first()
        if consignor:
            data = {
                'sender_mobile': consignor.sender_mobile,
                'sender_email': consignor.sender_email,
                'sender_GST': consignor.sender_GST,
                'sender_address': consignor.sender_address,
                'sender_company': consignor.sender_company,
            }
        else:
            data = {}
    else:
        data = {}

    return JsonResponse(data)

def get_consignee_name(request):
    query = request.GET.get('query', '')
    if query:
        receiver_names = Consignee.objects.filter(receiver_name__icontains=query).values_list('receiver_name', flat=True)
        print('sender_names numbers:', list(receiver_names))  # Debugging: check the data in the terminal
        return JsonResponse(list(receiver_names), safe=False)
    return JsonResponse([], safe=False)

def get_rec_details(request):
    name = request.GET.get('name', '')
    if name:
        consignee = Consignee.objects.filter(receiver_name=name).first()
        if consignee:
            data = {
                'receiver_mobile': consignee.receiver_mobile,
                'receiver_GST': consignee.receiver_GST,
                'receiver_email': consignee.receiver_email,
                'receiver_address': consignee.receiver_address,
                'receiver_company': consignee.receiver_company,
            }
        else:
            data = {}
    else:
        data = {}

    return JsonResponse(data)

def branchConsignment(request):
    if request.method == "POST":

        now = datetime.now()
        con_date = now.strftime("%Y-%m-%d")

        # Get the last track_id and increment it
        last_track_id = AddConsignment.objects.aggregate(Max('track_id'))['track_id__max']
        track_id = int(last_track_id) + 1 if last_track_id else 1000  # Start from a defined base if no entries exist
        con_id = str(track_id)

        # Get the last Consignment_id and increment it
        last_con_id = AddConsignment.objects.aggregate(Max('Consignment_id'))['Consignment_id__max']
        Consignment_id = last_con_id + 1 if last_con_id else 1000  # Start from a defined base if no entries exist
        Consignment_id = str(Consignment_id)

        # Sender details
        send_name = request.POST.get('a1')
        send_mobile = request.POST.get('a2')
        send_email = request.POST.get('a3')
        send_address = request.POST.get('a4')
        sender_GST = request.POST.get('sendergst')
        sender_company = request.POST.get('sen_company')

        # Receiver details
        rec_name = request.POST.get('a5')
        rec_mobile = request.POST.get('a6')
        rec_email = request.POST.get('a7')
        rec_address = request.POST.get('a8')
        rec_GST = request.POST.get('receivergst')
        rec_company = request.POST.get('receiverCompany')

        copies = []
        if request.POST.get('consignor_copy'):
            copies.append('Consignor Copy')
        if request.POST.get('consignee_copy'):
            copies.append('Consignee Copy')
        if request.POST.get('lorry_copy'):
            copies.append('Lorry Copy')
        copy_type = ', '.join(copies)  # Combine into a single string

        # Create or update Consignor
        consignor, created = Consignor.objects.update_or_create(
            sender_email=send_email,
            defaults={
                'sender_name': send_name,
                'sender_mobile': send_mobile,
                'sender_address': send_address,
                'sender_GST': sender_GST,
                'sender_company': sender_company
            }
        )

        # Create or update Consignee
        consignee, created = Consignee.objects.update_or_create(
            receiver_email=rec_email,
            defaults={
                'receiver_name': rec_name,
                'receiver_mobile': rec_mobile,
                'receiver_address': rec_address,
                'receiver_GST': rec_GST,
                'receiver_company': rec_company
            }
        )

        # Handling product entries
        products = request.POST.getlist('product[]')
        pieces = request.POST.getlist('pieces[]')

        # Other consignment details
        prod_invoice = request.POST.get('prod_invoice')
        prod_price = request.POST.get('prod_price')


        weight = float(request.POST.get('weight'))
        freight = float(request.POST.get('freight'))
        hamali = float(request.POST.get('hamali'))
        door_charge = float(request.POST.get('door_charge'))
        st_charge = float(request.POST.get('st_charge'))
        bal = float(request.POST.get('bal'))

        route_from = request.POST.get('from')
        route_to = request.POST.get('to')
        cost = float(request.POST.get('cost'))

        pay_status = request.POST.get('payment')

        current_time = now.strftime("%H:%M:%S")

        uid = request.session.get('username')
        branch = Branch.objects.get(email=uid)
        uname = branch.companyname
        username = branch.headname

        utype = request.session.get('utype')
        branch_value = 'admin' if utype == 'admin' else uname

        # Loop through products and save each one
        for product, piece in zip(products, pieces):
            # Skip rows where product or piece is empty
            if not product or not piece:
                continue
            AddConsignment.objects.create(
                track_id=con_id,
                Consignment_id=Consignment_id,
                sender_name=send_name,
                sender_mobile=send_mobile,
                sender_email=send_email,
                sender_address=send_address,
                sender_GST=sender_GST,
                sender_company=sender_company,
                receiver_name=rec_name,
                receiver_mobile=rec_mobile,
                receiver_email=rec_email,
                receiver_address=rec_address,
                receiver_GST=rec_GST,
                receiver_company=rec_company,
                desc_product=product,
                pieces=piece,
                prod_invoice=prod_invoice,
                prod_price=prod_price,
                weight=weight,
                freight=freight,
                hamali=hamali,
                door_charge=door_charge,
                st_charge=st_charge,
                balance=bal,
                route_from=route_from,
                route_to=route_to,
                total_cost=cost,
                date=con_date,
                pay_status=pay_status,
                branch=branch_value,
                name=username,
            time=current_time,
            copy_type=copy_type)

        for product, piece in zip(products, pieces):
            # Skip rows where product or piece is empty
            if not product or not piece:
                continue

            AddConsignmentTemp.objects.create(
                track_id=con_id,
                Consignment_id=Consignment_id,
                sender_name=send_name,
                sender_mobile=send_mobile,
                sender_email=send_email,
                sender_address=send_address,
                sender_GST=sender_GST,
                sender_company=sender_company,
                receiver_name=rec_name,
                receiver_mobile=rec_mobile,
                receiver_email=rec_email,
                receiver_address=rec_address,
                receiver_GST=rec_GST,
                receiver_company=rec_company,
                desc_product=product,
                pieces=piece,  # Assign the current piece to the pieces field
                prod_invoice=prod_invoice,
                prod_price=prod_price,
                weight=weight,
                freight=freight,
                hamali=hamali,
                door_charge=door_charge,
                st_charge=st_charge,
                balance=bal,
                route_from=route_from,
                route_to=route_to,
                total_cost=cost,
                date=con_date,
                pay_status=pay_status,
                branch=branch_value,
                name=username,
                time=current_time,
                copy_type=copy_type
            )
            # Initialize balance based on sender_name if it's the first entry for that sender
            previous_balance_entry = Account.objects.filter(sender_name=send_name).order_by('-Date').first()
            if previous_balance_entry:
                previous_balance = float(previous_balance_entry.Balance)
            else:
                previous_balance = 0.0  # Initialize balance to 0 if no previous entries

            # Update the current balance for the sender
            updated_balance = previous_balance + cost

            # Create the Account model entry
            Account.objects.create(
                Date=now,  # Use current date and time
                track_number=con_id,
                debit=str(cost),
                credit="0",
                TrType="sal",
                particulars=f"{con_id} Debited",  # Use f-string for dynamic insertion
                Balance=str(updated_balance),
                sender_name=send_name,
                headname=username,  # Save the headname in the Account model as well
            )
        # Generate a random password
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for i in range(8))

        # Check if the user already exists
        user, created = Login.objects.update_or_create(
            username=rec_email,
            defaults={
                'password': password,  # Store the password directly
                'utype': 'user'
            }
        )

        if created:
            print("New user created with password:", password)
        else:
            print("User already exists. Updated password to:", password)

        return redirect('branchprintConsignment', track_id=con_id)

    else:
        # Fetch the vehicle numbers from the Driver model
        vehicle_numbers = Driver.objects.values_list('vehicle_number', flat=True)

        # Pass vehicle numbers to the template
        return render(request, 'branchConsignment.html')


def branchprintConsignment(request, track_id):
    # Filter consignments by track_id
    consignments = AddConsignment.objects.filter(track_id=track_id)
    uid = request.session.get('username')
    branchdetails = Branch.objects.get(email=uid)

    if not consignments.exists():
        return render(request, '404.html')  # Handle the case where no consignments are found.

    # Get common details from the first consignment
    consignment = consignments.first()

    # Collect copy_types from all consignments with the same track_id
    copy_types = consignments.values_list('copy_type', flat=True).distinct()

    # Convert the queryset to a list and join them into a single string for display
    copy_type_list = ', '.join(copy_types)

    # Pass the first consignment, the entire list of items, and the copy types to the template
    return render(request, 'printConsignment.html', {
        'consignment': consignment,
        'items': consignments,
        'branchdetails': branchdetails,
        'copy_types': copy_type_list  # Include the aggregated copy types
    })


def branchviewConsignment(request):
    uid = request.session.get('username')
    userdata = AddConsignment.objects.none()

    if uid:
        try:
            branch = Branch.objects.get(email=uid)
            user_branch = branch.companyname  # Adjust if the branch info is stored differently

            userdata = AddConsignment.objects.filter(branch=user_branch)

        except ObjectDoesNotExist:
            userdata = AddConsignment.objects.none()

    return render(request, 'branchviewConsignment.html', {'userdata': userdata})

def branchMaster(request):
    uid = request.session['username']
    email=Branch.objects.get(email=uid)
    bid = email.id
    data = Branch.objects.filter(id=bid).first()  # Retrieve a single object or None
    if request.method == "POST":
        companyname = request.POST.get('companyname')
        phonenumber = request.POST.get('phonenumber')
        email = request.POST.get('email')
        gst = request.POST.get('gst')
        address = request.POST.get('address')
        image= request.POST.get('image')

        # Update the object
        data.companyname = companyname
        data.phonenumber = phonenumber
        data.email = email
        data.gst = gst
        data.address = address
        data.image=image

        data.save()

        # Redirect to a different URL after successful update
        base_url = reverse('branchMaster')
        return redirect(base_url)

    return render(request, 'branchMaster.html', {'data': data})

def branchconsignment_edit(request, pk):
    userdata = AddConsignment.objects.filter(id=pk).first()  # Retrieve a single object or None


    if request.method == "POST":
        track_id = userdata.track_id
        con_date = userdata.date

        send_name = request.POST.get('a1')
        send_mobile = request.POST.get('a2')
        send_email = request.POST.get('a3')
        send_address = request.POST.get('a4')

        rec_name = request.POST.get('a5')
        rec_mobile = request.POST.get('a6')
        rec_email = request.POST.get('a7')
        rec_address = request.POST.get('a8')

        cost = request.POST.get('a9')

        # Update the object
        userdata.track_no = track_id
        userdata.sender_name = send_name
        userdata.sender_mobile = send_mobile
        userdata.sender_email = send_email
        userdata.sender_address = send_address
        userdata.receiver_name = rec_name
        userdata.receiver_mobile = rec_mobile
        userdata.receiver_email = rec_email
        userdata.receiver_address = rec_address
        userdata.total_cost = cost
        userdata.date = con_date
        userdata.save()

        # Redirect to a different URL after successful update
        base_url = reverse('branchviewConsignment')
        return redirect(base_url)

    return render(request, 'branchconsignment_edit.html', {'userdata': userdata})


def branchconsignment_delete(request,pk):
    udata=AddConsignment.objects.get(id=pk)
    udata.delete()
    base_url=reverse('view_consignment')
    return redirect(base_url)


def branchinvoiceConsignment(request, pk):
    consignment = get_object_or_404(AddConsignment, id=pk)
    branch = consignment.branch
    branchdetails = get_object_or_404(Branch, companyname=branch)
    return render(request, 'branchinvoiceConsignment.html', {'consignment': consignment,'branchdetails':branchdetails})

def branchaddTrack(request):
    userid = request.session.get('username')
    userdata = Branch.objects.get(email=userid)
    uname = userdata.companyname
    consignments = AddConsignment.objects.filter(branch=uname).order_by('-id')

    if request.method == "POST":
        now = datetime.datetime.now()
        con_date = now.strftime("%Y-%m-%d")

        track_id = request.POST.get('a1')
        status = request.POST.get('status')  # Retrieve status from the form

        # Retrieve custom status if "Other" is selected
        if status == "Other":
            custom_status = request.POST.get('a2')
        else:
            custom_status = None

        # Retrieve username from session and fetch the corresponding branch
        uid = request.session.get('username')

        if uid:
                userdata = Branch.objects.get(email=uid)
                uname = userdata.companyname

                # Check utype to determine the branch value
                utype = request.session.get('utype')
                branch_value = 'admin' if utype == 'admin' else uname

                # Filter consignment data based on the branch
                consignments = AddConsignment.objects.filter(branch=uname).order_by('-id')

                # Create AddTrack object
                AddTrack.objects.create(
                    track_id=track_id,
                    description=status,
                    date=con_date,
                    branch=branch_value
                )

        else:
            # Handle the case where session data is missing
            consignments = AddConsignment.objects.none()
            return render(request, 'branchaddTrack.html', {'consignments': consignments, 'msg': 'Session data missing'})

    return render(request, 'branchaddTrack.html', {'consignments': consignments})


def branchsearch_results(request):
    tracker_id = request.GET.get('tracker_id')
    userid = request.session.get('username')
    userdata = Branch.objects.get(email=userid)
    uname = userdata.companyname
    consignments = AddConsignment.objects.filter(branch=uname).order_by('-id')

    if tracker_id:
        try:
            trackers = AddTrack.objects.filter(track_id=tracker_id)
            if trackers.exists():
                return render(request, 'branchsearch_results.html', {'trackers': trackers, 'consignments': consignments})
            else:
                message = f"No tracking information found for ID: {tracker_id}"
                return render(request, 'branchsearch_results.html', {'message': message, 'consignments': consignments})
        except Exception as e:
            message = f"Error occurred: {str(e)}"
            return render(request, 'branchsearch_results.html', {'message': message, 'consignments': consignments})
    else:
        return render(request, 'branchsearch_results.html', {'message': "Please enter a tracker ID.", 'consignments': consignments})


def branchtrack_delete(request,pk):
    udata=AddTrack.objects.get(id=pk)
    udata.delete()
    base_url=reverse('branchsearch_results')
    return redirect(base_url)


def get_vehicle_numbers(request):
    query = request.GET.get('query', '')
    if query:
        vehicle_numbers = Driver.objects.filter(vehicle_number__icontains=query).values_list('vehicle_number', flat=True)
        print('Vehicle numbers:', list(vehicle_numbers))  # Debugging: check the data in the terminal
        return JsonResponse(list(vehicle_numbers), safe=False)
    return JsonResponse([], safe=False)

def get_branch(request):
    query = request.GET.get('query', '')
    if query:
        companyname = Branch.objects.filter(companyname__icontains=query).values_list('companyname', flat=True)
        print('Branch Name:', list(companyname))  # Debugging: check the data in the terminal
        return JsonResponse(list(companyname), safe=False)
    return JsonResponse([], safe=False)

def get_destination(request):
    query = request.GET.get('query', '')
    if query:
        # Filter and get distinct route_to values
        route_to = AddConsignment.objects.filter(route_to__icontains=query).values_list('route_to', flat=True).distinct()
        print('Distinct route_to numbers:', list(route_to))  # Debugging: check the data in the terminal
        return JsonResponse(list(route_to), safe=False)
    return JsonResponse([], safe=False)




from collections import defaultdict

def addTripSheet(request):
    return render(request,'addTripSheet.html')
def addTripSheetList(request):
    route_to = AddConsignmentTemp.objects.values_list('route_to', flat=True).distinct()
    addtrip = defaultdict(lambda: {'desc_product': [], 'pieces': 0, 'receiver_name': '', 'pay_status': '','route_to':'','total':'','freight':'','hamali':'','door_charge':'','st_charge':''})
    no_data_found = False  # Flag to check if data was found

    uid = request.session.get('username')
    if uid:
        try:
            branch = Branch.objects.get(email=uid)
            user_branch = branch.companyname

            if request.method == 'POST':
                route_to = request.POST.get('dest')
                date = request.POST.get('date')

                if date:
                    consignments = AddConsignmentTemp.objects.filter(
                        route_to=route_to,
                        date=date,
                        branch=user_branch
                    )

                    if consignments.exists():
                        for consignment in consignments:
                            consignment_data = addtrip[consignment.track_id]
                            consignment_data['desc_product'].append(consignment.desc_product)
                            consignment_data['pieces'] += consignment.pieces
                            consignment_data['route_to'] = consignment.route_to
                            consignment_data['receiver_name'] = consignment.receiver_name
                            consignment_data['pay_status'] = consignment.pay_status
                            consignment_data['total_cost'] = consignment.total_cost
                            consignment_data['freight'] = consignment.freight
                            consignment_data['hamali'] = consignment.hamali
                            consignment_data['door_charge'] = consignment.door_charge
                            consignment_data['st_charge'] = consignment.st_charge
                    else:
                        no_data_found = True  # Set the flag if no data is found

            addtrip = [
                {
                    'track_id': track_id,
                    'desc_product': ', '.join(consignment_data['desc_product']),
                    'pieces': consignment_data['pieces'],
                    'route_to': consignment_data['route_to'],
                    'receiver_name': consignment_data['receiver_name'],
                    'pay_status': consignment_data['pay_status'],
                    'total_cost': consignment_data['total_cost'],
                    'freight': consignment_data['freight'],
                    'hamali': consignment_data['hamali'],
                    'door_charge': consignment_data['door_charge'],
                    'st_charge': consignment_data['st_charge']
                }
                for track_id, consignment_data in addtrip.items()
            ]

        except Branch.DoesNotExist:
            addtrip = []
            no_data_found = True  # Set the flag if the branch does not exist

    return render(request, 'addTripSheetList.html', {
        'route_to': route_to,
        'trip': addtrip,
        'no_data_found': no_data_found  # Pass the flag to the template
    })

def saveTripSheet(request):
    print("saveTripSheet function called")
    if request.method == 'POST':
        print("POST request received")  # Debugging statement

        last_trip_id = TripSheetPrem.objects.aggregate(Max('trip_id'))['trip_id__max']
        trip_id = int(last_trip_id) + 1 if last_trip_id else 1000  # Start from a defined base if no entries exist
        con_id = str(trip_id)

        uid = request.session.get('username')
        if uid:
            try:
                branch = Branch.objects.get(email=uid)
                branchname = branch.companyname
                username = branch.headname

                now = datetime.now()
                con_date = now.strftime("%Y-%m-%d")
                current_time = now.strftime("%H:%M:%S")

                vehicle = request.POST.get('vehical')
                adv = request.POST.get('advance')
                ltrate = request.POST.get('ltrate')
                ltr = request.POST.get('liter')
                commission = request.POST.get('commission')
                vehicaldet = Driver.objects.get(vehicle_number=vehicle)
                drivername = vehicaldet.driver_name
                total_rows = int(request.POST.get('total_rows', 0))

                print(f"Vehicle: {vehicle}, Driver Name: {drivername}")  # Debugging statement

                for i in range(1, total_rows + 1):
                    track_id = request.POST.get(f'track_id_{i}')
                    pieces = request.POST.get(f'pieces_{i}')
                    desc_product = request.POST.get(f'desc_product_{i}')
                    route_to = request.POST.get(f'route_to_{i}')
                    receiver_name = request.POST.get(f'receiver_name_{i}')
                    pay_status = request.POST.get(f'pay_status_{i}')
                    total_cost = request.POST.get(f'total_cost{i}')
                    freight = request.POST.get(f'freight{i}')
                    hamali = request.POST.get(f'hamali{i}')
                    door_charge = request.POST.get(f'door_charge{i}')
                    st_charge = request.POST.get(f'st_charge{i}')

                    print(f"Track ID: {track_id}, Pieces: {pieces}, Description: {desc_product}, Route: {route_to}, Receiver: {receiver_name}, Pay Status: {pay_status}, total_cost:{total_cost},freight:{freight},hamali:{hamali},door_charge:{door_charge},st_charge:{st_charge}")  # Debugging statement

                    try:
                        # Save to TripSheetTemp
                        TripSheetTemp.objects.create(
                            LRno=track_id,
                            qty=pieces,
                            desc=desc_product,
                            dest=route_to,
                            consignee=receiver_name,
                            pay_status=pay_status,
                            VehicalNo=vehicle,
                            DriverName=drivername,
                            branch=branchname,
                            username=username,
                            Date=con_date,
                            Time=current_time,
                            AdvGiven=adv,
                            LTRate=ltrate,
                            Ltr=ltr,
                            commission=commission,
                            total_cost=total_cost,
                            freight=freight,
                            hamali=hamali,
                            door_charge=door_charge,
                            st_charge=st_charge,
                            trip_id=con_id
                        )

                        # Save to TripSheetPrem
                        TripSheetPrem.objects.create(
                            LRno=track_id,
                            qty=pieces,
                            desc=desc_product,
                            dest=route_to,
                            consignee=receiver_name,
                            pay_status=pay_status,
                            VehicalNo=vehicle,
                            DriverName=drivername,
                            branch=branchname,
                            username=username,
                            Date=con_date,
                            Time=current_time,
                            AdvGiven=adv,
                            LTRate=ltrate,
                            Ltr=ltr,
                            commission=commission,
                            total_cost=total_cost,
                            freight=freight,
                            hamali=hamali,
                            door_charge=door_charge,
                            st_charge=st_charge,
                            trip_id=con_id
                        )

                        # Delete from AddConsignmentTemp
                        AddConsignmentTemp.objects.filter(track_id=track_id).delete()

                        print(f"Data for Track ID {track_id} saved and deleted from AddConsignmentTemp successfully.")  # Debugging statement

                    except Exception as e:
                        print(f"Error saving or deleting data for Track ID {track_id}: {e}")  # Debugging statement

            except Branch.DoesNotExist:
                print("Branch does not exist.")  # Debugging statement
        else:
            print("No username found in session.")  # Debugging statement

        return redirect('addTripSheet')  # Replace with your desired success URL

    print("Not a POST request, redirecting back to form.")  # Debugging statement
    return render(request, 'addTripSheetList.html')  # Redirect back to the form if not a POST request


from django.db.models import Sum, F, FloatField

def tripSheet(request):
    return render(request,'tripSheet.html')

def tripSheetList(request):
    trips = []
    total_value = 0
    total_qty = 0
    grand_total = {
        'toPay': 0,
        'paid': 0,
        'AC': 0,
        'grand_freight': 0,
        'grand_hamali': 0,
        'grand_door_charge': 0,
        'grand_st_charge': 0,
        'grand_total': 0
    }
    summary = {
        'toPay': {'freight': 0, 'hamali': 0, 'st_charge': 0, 'door_charge': 0, 'total_cost': 0},
        'paid': {'freight': 0, 'hamali': 0, 'st_charge': 0, 'door_charge': 0, 'total_cost': 0},
        'AC': {'freight': 0, 'hamali': 0, 'st_charge': 0, 'door_charge': 0, 'total_cost': 0}
    }

    uid = request.session.get('username')

    if uid:
        try:
            branch = Branch.objects.get(email=uid)
            user_branch = branch.companyname

            if request.method == 'POST':
                vehicle_number = request.POST.get('vehical')
                date = request.POST.get('t3')

                if date:
                    trips = TripSheetPrem.objects.filter(
                        VehicalNo=vehicle_number,
                        Date=date,
                        branch=user_branch
                    )
                    total_qty = trips.aggregate(total_qty=Sum('qty'))['total_qty'] or 0

                    # Initialize grand totals for each pay_status
                    grand_total['toPay'] = 0
                    grand_total['paid'] = 0
                    grand_total['AC'] = 0
                    grand_total['grand_freight'] = 0
                    grand_total['grand_hamali'] = 0
                    grand_total['grand_door_charge'] = 0
                    grand_total['grand_st_charge'] = 0
                    grand_total['grand_total'] = 0

                    # Aggregate data based on pay_status
                    statuses = ['toPay', 'paid', 'AC']
                    for status in statuses:
                        status_trips = trips.filter(pay_status=status)
                        summary[status]['freight'] = status_trips.aggregate(total=Sum('freight'))['total'] or 0
                        summary[status]['hamali'] = status_trips.aggregate(total=Sum('hamali'))['total'] or 0
                        summary[status]['st_charge'] = status_trips.aggregate(total=Sum('st_charge'))['total'] or 0
                        summary[status]['door_charge'] = status_trips.aggregate(total=Sum('door_charge'))['total'] or 0
                        summary[status]['total_cost'] = status_trips.aggregate(total=Sum('total_cost'))['total'] or 0

                        # Update grand totals
                        grand_total[status] = summary[status]['total_cost']
                        grand_total['grand_freight'] += summary[status]['freight']
                        grand_total['grand_hamali'] += summary[status]['hamali']
                        grand_total['grand_st_charge'] += summary[status]['st_charge']
                        grand_total['grand_door_charge'] += summary[status]['door_charge']
                        grand_total['grand_total'] += summary[status]['total_cost']

                    # Calculate the total value using only the first row
                    if trips.exists():
                        first_trip = trips.first()
                        total_ltr_value = float(
                            first_trip.LTRate * first_trip.Ltr) if first_trip.LTRate and first_trip.Ltr else 0.0
                        total_adv_given = float(first_trip.AdvGiven) if first_trip.AdvGiven else 0.0
                        total_commission = float(first_trip.commission) if first_trip.commission else 0.0
                        total_value = total_ltr_value + total_adv_given + total_commission
                    else:
                        total_value = 0.0

        except ObjectDoesNotExist:
            trips = TripSheetTemp.objects.none()

    return render(request, 'TripSheetList.html', {
        'trips': trips,
        'total_value': total_value,
        'total_qty': total_qty,
        'grand_total': grand_total,
        'summary': summary
    })


@require_POST
def delete_trip_sheet_data(request):
    vehicle_number = request.POST.get('vehical')
    date = request.POST.get('t3')
    uid = request.session.get('username')

    print(f"Received vehicle_number: {vehicle_number}, date: {date}, uid: {uid}")

    if uid and vehicle_number and date:
        try:
            branch = Branch.objects.get(email=uid)
            user_branch = branch.companyname
            TripSheetTemp.objects.filter(
                VehicalNo=vehicle_number,
                Date=date,
                branch=user_branch
            ).delete()
            return JsonResponse({'status': 'success'})
        except ObjectDoesNotExist:
            print("Branch does not exist.")
            return JsonResponse({'status': 'error', 'message': 'Branch does not exist'})

    print("Invalid parameters received.")
    return JsonResponse({'status': 'error', 'message': 'Invalid parameters'})
def viewTripSheetList(request):
    grouped_trips = []
    uid = request.session.get('username')

    if uid:
        try:
            branch = Branch.objects.get(email=uid)
            user_branch = branch.companyname

            if request.method == 'POST':
                date = request.POST.get('t3')

                if date:
                    # Group by VehicalNo and Date, and annotate with count
                    grouped_trips = (
                        TripSheetPrem.objects
                        .filter(Date=date, branch=user_branch)
                        .values('VehicalNo', 'Date')
                        .annotate(trip_count=Count('id'))
                    )

        except ObjectDoesNotExist:
            grouped_trips = []

    return render(request, 'viewTripSheetList.html', {
        'grouped_trips': grouped_trips
    })

def editTripSheetList(request):
    trips = []
    total_value = 0
    total_qty = 0
    grand_total = {
        'toPay': 0,
        'paid': 0,
        'AC': 0,
        'grand_freight': 0,
        'grand_hamali': 0,
        'grand_door_charge': 0,
        'grand_st_charge': 0,
        'grand_total': 0
    }
    summary = {
        'toPay': {'freight': 0, 'hamali': 0, 'st_charge': 0, 'door_charge': 0, 'total_cost': 0},
        'paid': {'freight': 0, 'hamali': 0, 'st_charge': 0, 'door_charge': 0, 'total_cost': 0},
        'AC': {'freight': 0, 'hamali': 0, 'st_charge': 0, 'door_charge': 0, 'total_cost': 0}
    }

    uid = request.session.get('username')

    if uid:
        try:
            branch = Branch.objects.get(email=uid)
            user_branch = branch.companyname

            if request.method == 'POST':
                vehicle_number = request.POST.get('vehical')
                date_str  = request.POST.get('t3')

                if date_str:
                    try:
                        # Example format to parse. Adjust as needed.
                        date = datetime.strptime(date_str, "%b. %d, %Y").strftime("%Y-%m-%d")
                    except ValueError:
                        raise ValidationError(f'Invalid date format: {date_str}')
                    trips = TripSheetPrem.objects.filter(
                        VehicalNo=vehicle_number,
                        Date=date,
                        branch=user_branch
                    )
                    total_qty = trips.aggregate(total_qty=Sum('qty'))['total_qty'] or 0

                    # Initialize grand totals for each pay_status
                    grand_total['toPay'] = 0
                    grand_total['paid'] = 0
                    grand_total['AC'] = 0
                    grand_total['grand_freight'] = 0
                    grand_total['grand_hamali'] = 0
                    grand_total['grand_door_charge'] = 0
                    grand_total['grand_st_charge'] = 0
                    grand_total['grand_total'] = 0

                    # Aggregate data based on pay_status
                    statuses = ['toPay', 'paid', 'AC']
                    for status in statuses:
                        status_trips = trips.filter(pay_status=status)
                        summary[status]['freight'] = status_trips.aggregate(total=Sum('freight'))['total'] or 0
                        summary[status]['hamali'] = status_trips.aggregate(total=Sum('hamali'))['total'] or 0
                        summary[status]['st_charge'] = status_trips.aggregate(total=Sum('st_charge'))['total'] or 0
                        summary[status]['door_charge'] = status_trips.aggregate(total=Sum('door_charge'))['total'] or 0
                        summary[status]['total_cost'] = status_trips.aggregate(total=Sum('total_cost'))['total'] or 0

                        # Update grand totals
                        grand_total[status] = summary[status]['total_cost']
                        grand_total['grand_freight'] += summary[status]['freight']
                        grand_total['grand_hamali'] += summary[status]['hamali']
                        grand_total['grand_st_charge'] += summary[status]['st_charge']
                        grand_total['grand_door_charge'] += summary[status]['door_charge']
                        grand_total['grand_total'] += summary[status]['total_cost']

                    # Calculate the total value using only the first row
                    if trips.exists():
                        first_trip = trips.first()
                        total_ltr_value = float(
                            first_trip.LTRate * first_trip.Ltr) if first_trip.LTRate and first_trip.Ltr else 0.0
                        total_adv_given = float(first_trip.AdvGiven) if first_trip.AdvGiven else 0.0
                        total_commission = float(first_trip.commission) if first_trip.commission else 0.0
                        total_value = total_ltr_value + total_adv_given + total_commission
                    else:
                        total_value = 0.0

        except ObjectDoesNotExist:
            trips = TripSheetTemp.objects.none()

    return render(request, 'editTripSheetList.html', {
        'trips': trips,
        'total_value': total_value,
        'total_qty': total_qty,
        'grand_total': grand_total,
        'summary': summary
    })


def update_view(request):
    if request.method == "POST":
        trip_id = request.POST.get("trip_id")
        print(f"Received trip_id: {trip_id}")  # Debugging line

        # Fetch all records with the matching trip_id
        trips = TripSheetPrem.objects.filter(trip_id=trip_id)

        if trips.exists():
            print(f"Found {trips.count()} trip records to update")
            for trip in trips:
                # Update the fields for each trip
                trip.LTRate = request.POST.get("ltrate")
                trip.Ltr = request.POST.get("ltr")
                trip.AdvGiven = request.POST.get("advgiven")
                trip.commission = request.POST.get("commission")
                trip.save()

            # Redirect after saving
            return redirect('viewTripSheetList')  # Replace with your success URL
        else:
            print("No trip records found")
            return render(request, 'editTripSheetList.html', {'error_message': 'No trips found with the provided trip_id.'})

    return render(request, 'editTripSheetList.html')  # Replace with your template

def printTripSheetList(request, vehical_no, date):
    trips = []
    total_value = 0
    total_qty = 0
    grand_total = {
        'toPay': 0,
        'paid': 0,
        'AC': 0,
        'grand_freight': 0,
        'grand_hamali': 0,
        'grand_door_charge': 0,
        'grand_st_charge': 0,
        'grand_total': 0
    }
    summary = {
        'toPay': {'freight': 0, 'hamali': 0, 'st_charge': 0, 'door_charge': 0, 'total_cost': 0},
        'paid': {'freight': 0, 'hamali': 0, 'st_charge': 0, 'door_charge': 0, 'total_cost': 0},
        'AC': {'freight': 0, 'hamali': 0, 'st_charge': 0, 'door_charge': 0, 'total_cost': 0}
    }

    uid = request.session.get('username')

    if uid:
        try:
            branch = Branch.objects.get(email=uid)
            user_branch = branch.companyname

            # Filter trips based on VehicleNo, Date, and branch
            trips = TripSheetPrem.objects.filter(
                VehicalNo=vehical_no,
                Date=date,
                branch=user_branch
            )

            # Calculate total quantity
            total_qty = trips.aggregate(total_qty=Sum('qty'))['total_qty'] or 0

            # Aggregate data based on pay_status
            statuses = ['toPay', 'paid', 'AC']
            for status in statuses:
                status_trips = trips.filter(pay_status=status)
                summary[status]['freight'] = status_trips.aggregate(total=Sum('freight'))['total'] or 0
                summary[status]['hamali'] = status_trips.aggregate(total=Sum('hamali'))['total'] or 0
                summary[status]['st_charge'] = status_trips.aggregate(total=Sum('st_charge'))['total'] or 0
                summary[status]['door_charge'] = status_trips.aggregate(total=Sum('door_charge'))['total'] or 0
                summary[status]['total_cost'] = status_trips.aggregate(total=Sum('total_cost'))['total'] or 0

                # Update grand totals
                grand_total[status] = summary[status]['total_cost']
                grand_total['grand_freight'] += summary[status]['freight']
                grand_total['grand_hamali'] += summary[status]['hamali']
                grand_total['grand_st_charge'] += summary[status]['st_charge']
                grand_total['grand_door_charge'] += summary[status]['door_charge']
                grand_total['grand_total'] += summary[status]['total_cost']

            # Calculate the total value using the first row
            if trips.exists():
                first_trip = trips.first()
                total_ltr_value = float(first_trip.LTRate * first_trip.Ltr) if first_trip.LTRate and first_trip.Ltr else 0.0
                total_adv_given = float(first_trip.AdvGiven) if first_trip.AdvGiven else 0.0
                total_commission = float(first_trip.commission) if first_trip.commission else 0.0
                total_value = total_ltr_value + total_adv_given + total_commission
            else:
                total_value = 0.0

        except Branch.DoesNotExist:
            trips = TripSheetPrem.objects.none()  # Handle case where Branch does not exist

    return render(request, 'printTripSheetList.html', {
        'trips': trips,
        'total_value': total_value,
        'total_qty': total_qty,
        'grand_total': grand_total,
        'summary': summary
    })



def adminTripSheet(request):
    grouped_trips = []

    if request.method == 'POST':
        vehicle_number = request.POST.get('vehical')
        branch = request.POST.get('t2')
        date = request.POST.get('t3')

        if date:
            # Group by VehicalNo and Date, and annotate with count
            grouped_trips = (
                TripSheetPrem.objects
                .filter(Date=date, VehicalNo=vehicle_number,branch=branch)
                .values('VehicalNo', 'Date')
                .annotate(trip_count=Count('id'))
            )
    return render(request, 'adminTripSheet.html', {
        'grouped_trips': grouped_trips
    })

def adminPrintTripSheetList(request, vehical_no, date):
    trips = []
    total_value = 0
    total_qty = 0
    grand_total = {
        'toPay': 0,
        'paid': 0,
        'AC': 0,
        'grand_freight': 0,
        'grand_hamali': 0,
        'grand_door_charge': 0,
        'grand_st_charge': 0,
        'grand_total': 0
    }
    summary = {
        'toPay': {'freight': 0, 'hamali': 0, 'st_charge': 0, 'door_charge': 0, 'total_cost': 0},
        'paid': {'freight': 0, 'hamali': 0, 'st_charge': 0, 'door_charge': 0, 'total_cost': 0},
        'AC': {'freight': 0, 'hamali': 0, 'st_charge': 0, 'door_charge': 0, 'total_cost': 0}
    }

    uid = request.session.get('username')

    if uid:
        try:
            branch = Branch.objects.get(email=uid)
            user_branch = branch.companyname

            # Filter trips based on VehicleNo, Date, and branch
            trips = TripSheetPrem.objects.filter(
                VehicalNo=vehical_no,
                Date=date,
                branch=user_branch
            )

            # Calculate total quantity
            total_qty = trips.aggregate(total_qty=Sum('qty'))['total_qty'] or 0

            # Aggregate data based on pay_status
            statuses = ['toPay', 'paid', 'AC']
            for status in statuses:
                status_trips = trips.filter(pay_status=status)
                summary[status]['freight'] = status_trips.aggregate(total=Sum('freight'))['total'] or 0
                summary[status]['hamali'] = status_trips.aggregate(total=Sum('hamali'))['total'] or 0
                summary[status]['st_charge'] = status_trips.aggregate(total=Sum('st_charge'))['total'] or 0
                summary[status]['door_charge'] = status_trips.aggregate(total=Sum('door_charge'))['total'] or 0
                summary[status]['total_cost'] = status_trips.aggregate(total=Sum('total_cost'))['total'] or 0

                # Update grand totals
                grand_total[status] = summary[status]['total_cost']
                grand_total['grand_freight'] += summary[status]['freight']
                grand_total['grand_hamali'] += summary[status]['hamali']
                grand_total['grand_st_charge'] += summary[status]['st_charge']
                grand_total['grand_door_charge'] += summary[status]['door_charge']
                grand_total['grand_total'] += summary[status]['total_cost']

            # Calculate the total value using the first row
            if trips.exists():
                first_trip = trips.first()
                total_ltr_value = float(first_trip.LTRate * first_trip.Ltr) if first_trip.LTRate and first_trip.Ltr else 0.0
                total_adv_given = float(first_trip.AdvGiven) if first_trip.AdvGiven else 0.0
                total_commission = float(first_trip.commission) if first_trip.commission else 0.0
                total_value = total_ltr_value + total_adv_given + total_commission
            else:
                total_value = 0.0

        except Branch.DoesNotExist:
            trips = TripSheetPrem.objects.none()  # Handle case where Branch does not exist

    return render(request, 'adminPrintTripSheetList.html', {
        'trips': trips,
        'total_value': total_value,
        'total_qty': total_qty,
        'grand_total': grand_total,
        'summary': summary
    })


@csrf_exempt
def save_location(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            city = data.get('city')

            if latitude and longitude:
                # Process the data, e.g., save to the database
                return JsonResponse({'status': 'success', 'message': 'Location saved'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Missing location data'}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

def staff(request):
    if request.method == "POST":

        uid = request.session.get('username')
        branch=Branch.objects.get(email=uid)
        branchname=branch.companyname

        staff = random.randint(111111, 999999)
        staffid = str(staff)

        staffname = request.POST.get('staffname')
        staffPhone = request.POST.get('staffPhone')
        staffaddress = request.POST.get('staffaddress')
        aadhar=request.POST.get('aadhar')

        utype = 'staff'


        Staff.objects.create(
            staffname=staffname,
            staffPhone=staffPhone,
            staffaddress=staffaddress,
            aadhar=aadhar,
            staffid=staffid,
            Branch=branchname

        )
        Login.objects.create(utype=utype, username=staffPhone, password=staffid,name=staffname)

    return render(request, 'staff.html')



def view_staff(request):
    data=Staff.objects.all()
    return render(request,'view_staff.html',{'data':data})


def delete_staff(request, pk):
    try:
        staff = Staff.objects.get(id=pk)

        user = Login.objects.filter(username=staff.staffPhone).first()
        if user:
            user.delete()
        staff.delete()

    except ObjectDoesNotExist:
        pass
    base_url = reverse('view_staff')
    return redirect(base_url)

def edit_staff(request, pk):
    # Retrieve the Staff record
    data = Staff.objects.filter(id=pk).first()  # Retrieve a single object or None

    if not data:
        return HttpResponse("Staff record not found.", status=404)

    # Store the original staffPhone
    original_staffPhone = data.staffPhone

    if request.method == "POST":
        # Get updated values from the POST request
        staffname = request.POST.get('staffname')
        staffPhone = request.POST.get('staffPhone')
        staffaddress = request.POST.get('staffaddress')
        aadhar = request.POST.get('aadhar')
        staffid = request.POST.get('staffid')

        # Update the Staff object
        data.staffname = staffname
        data.staffPhone = staffPhone
        data.staffaddress = staffaddress
        data.aadhar = aadhar
        data.staffid = staffid
        data.save()

        # Update the Login record using the original staffPhone
        user = Login.objects.filter(username=original_staffPhone).first()  # Fetch the user with the original phone number
        if user:
            user.username = staffPhone  # Update username to the new phone number
            user.name = staffname  # Update name
            user.password = staffid  # Update password if necessary
            user.save()

        # Redirect to a different URL after successful update
        base_url = reverse('view_staff')
        return redirect(base_url)

    return render(request, 'edit_staff.html', {'data': data})

def staffAddTripSheet(request):
    return render(request,'staffAddTripSheet.html')

def staffAddTripSheetList(request):
    route_to = AddConsignmentTemp.objects.values_list('route_to', flat=True).distinct()
    addtrip = defaultdict(lambda: {'desc_product': [], 'pieces': 0, 'receiver_name': '', 'pay_status': '','route_to':'','total':'','freight':'','hamali':'','door_charge':'','st_charge':''})
    no_data_found = False  # Flag to check if data was found

    uid = request.session.get('username')
    if uid:
        try:
            branch = Staff.objects.get(staffPhone=uid)
            user_branch = branch.Branch

            if request.method == 'POST':
                route_to = request.POST.get('dest')
                date = request.POST.get('date')

                if date:
                    consignments = AddConsignmentTemp.objects.filter(
                        route_to=route_to,
                        date=date,
                        branch=user_branch
                    )

                    if consignments.exists():
                        for consignment in consignments:
                            consignment_data = addtrip[consignment.track_id]
                            consignment_data['desc_product'].append(consignment.desc_product)
                            consignment_data['pieces'] += consignment.pieces
                            consignment_data['route_to'] = consignment.route_to
                            consignment_data['receiver_name'] = consignment.receiver_name
                            consignment_data['pay_status'] = consignment.pay_status
                            consignment_data['total_cost'] = consignment.total_cost
                            consignment_data['freight'] = consignment.freight
                            consignment_data['hamali'] = consignment.hamali
                            consignment_data['door_charge'] = consignment.door_charge
                            consignment_data['st_charge'] = consignment.st_charge
                    else:
                        no_data_found = True  # Set the flag if no data is found

            addtrip = [
                {
                    'track_id': track_id,
                    'desc_product': ', '.join(consignment_data['desc_product']),
                    'pieces': consignment_data['pieces'],
                    'route_to': consignment_data['route_to'],
                    'receiver_name': consignment_data['receiver_name'],
                    'pay_status': consignment_data['pay_status'],
                    'total_cost': consignment_data['total_cost'],
                    'freight': consignment_data['freight'],
                    'hamali': consignment_data['hamali'],
                    'door_charge': consignment_data['door_charge'],
                    'st_charge': consignment_data['st_charge']
                }
                for track_id, consignment_data in addtrip.items()
            ]

        except Branch.DoesNotExist:
            addtrip = []
            no_data_found = True  # Set the flag if the branch does not exist

    return render(request, 'staffAddTripSheetList.html', {
        'route_to': route_to,
        'trip': addtrip,
        'no_data_found': no_data_found  # Pass the flag to the template
    })

def staffSaveTripSheet(request):
    print("staffSaveTripSheet function called")
    if request.method == 'POST':
        print("POST request received")  # Debugging statement

        last_trip_id = TripSheetPrem.objects.aggregate(Max('trip_id'))['trip_id__max']
        trip_id = int(last_trip_id) + 1 if last_trip_id else 1000  # Start from a defined base if no entries exist
        con_id = str(trip_id)

        uid = request.session.get('username')
        if uid:
            try:
                branch = Staff.objects.get(staffPhone=uid)
                branchname = branch.Branch
                username = branch.staffname

                now = datetime.now()
                con_date = now.strftime("%Y-%m-%d")
                current_time = now.strftime("%H:%M:%S")

                vehicle = request.POST.get('vehical')
                adv = request.POST.get('advance')
                ltrate = request.POST.get('ltrate')
                ltr = request.POST.get('liter')
                commission = request.POST.get('commission')
                vehicaldet = Driver.objects.get(vehicle_number=vehicle)
                drivername = vehicaldet.driver_name
                total_rows = int(request.POST.get('total_rows', 0))

                print(f"Vehicle: {vehicle}, Driver Name: {drivername}")  # Debugging statement

                for i in range(1, total_rows + 1):
                    track_id = request.POST.get(f'track_id_{i}')
                    pieces = request.POST.get(f'pieces_{i}')
                    desc_product = request.POST.get(f'desc_product_{i}')
                    route_to = request.POST.get(f'route_to_{i}')
                    receiver_name = request.POST.get(f'receiver_name_{i}')
                    pay_status = request.POST.get(f'pay_status_{i}')
                    total_cost = request.POST.get(f'total_cost{i}')
                    freight = request.POST.get(f'freight{i}')
                    hamali = request.POST.get(f'hamali{i}')
                    door_charge = request.POST.get(f'door_charge{i}')
                    st_charge = request.POST.get(f'st_charge{i}')

                    print(f"Track ID: {track_id}, Pieces: {pieces}, Description: {desc_product}, Route: {route_to}, Receiver: {receiver_name}, Pay Status: {pay_status}, total_cost:{total_cost},freight:{freight},hamali:{hamali},door_charge:{door_charge},st_charge:{st_charge}")  # Debugging statement

                    try:
                        # Save to TripSheetTemp
                        TripSheetTemp.objects.create(
                            LRno=track_id,
                            qty=pieces,
                            desc=desc_product,
                            dest=route_to,
                            consignee=receiver_name,
                            pay_status=pay_status,
                            VehicalNo=vehicle,
                            DriverName=drivername,
                            branch=branchname,
                            username=username,
                            Date=con_date,
                            Time=current_time,
                            AdvGiven=adv,
                            LTRate=ltrate,
                            Ltr=ltr,
                            commission=commission,
                            total_cost=total_cost,
                            freight=freight,
                            hamali=hamali,
                            door_charge=door_charge,
                            st_charge=st_charge,
                            trip_id=con_id
                        )

                        # Save to TripSheetPrem
                        TripSheetPrem.objects.create(
                            LRno=track_id,
                            qty=pieces,
                            desc=desc_product,
                            dest=route_to,
                            consignee=receiver_name,
                            pay_status=pay_status,
                            VehicalNo=vehicle,
                            DriverName=drivername,
                            branch=branchname,
                            username=username,
                            Date=con_date,
                            Time=current_time,
                            AdvGiven=adv,
                            LTRate=ltrate,
                            Ltr=ltr,
                            commission=commission,
                            total_cost=total_cost,
                            freight=freight,
                            hamali=hamali,
                            door_charge=door_charge,
                            st_charge=st_charge,
                            trip_id=con_id
                        )

                        # Delete from AddConsignmentTemp
                        AddConsignmentTemp.objects.filter(track_id=track_id).delete()

                        print(f"Data for Track ID {track_id} saved and deleted from AddConsignmentTemp successfully.")  # Debugging statement

                    except Exception as e:
                        print(f"Error saving or deleting data for Track ID {track_id}: {e}")  # Debugging statement

            except Branch.DoesNotExist:
                print("Branch does not exist.")  # Debugging statement
        else:
            print("No username found in session.")  # Debugging statement

        return redirect('staffAddTripSheet')  # Replace with your desired success URL

    print("Not a POST request, redirecting back to form.")  # Debugging statement
    return render(request, 'staffAddTripSheetList.html')  # Redirect back to the form if not a POST request

def staffTripSheet(request):
    return render(request,'staffTripSheet.html')

def staffTripSheetList(request):
    trips = []
    total_value = 0
    total_qty = 0
    grand_total = {
        'toPay': 0,
        'paid': 0,
        'AC': 0,
        'grand_freight': 0,
        'grand_hamali': 0,
        'grand_door_charge': 0,
        'grand_st_charge': 0,
        'grand_total': 0
    }
    summary = {
        'toPay': {'freight': 0, 'hamali': 0, 'st_charge': 0, 'door_charge': 0, 'total_cost': 0},
        'paid': {'freight': 0, 'hamali': 0, 'st_charge': 0, 'door_charge': 0, 'total_cost': 0},
        'AC': {'freight': 0, 'hamali': 0, 'st_charge': 0, 'door_charge': 0, 'total_cost': 0}
    }

    uid = request.session.get('username')

    if uid:
        try:
            branch = Staff.objects.get(staffPhone=uid)
            user_branch = branch.Branch

            if request.method == 'POST':
                vehicle_number = request.POST.get('vehical')
                date = request.POST.get('t3')

                if date:
                    trips = TripSheetPrem.objects.filter(
                        VehicalNo=vehicle_number,
                        Date=date,
                        branch=user_branch
                    )
                    total_qty = trips.aggregate(total_qty=Sum('qty'))['total_qty'] or 0

                    # Initialize grand totals for each pay_status
                    grand_total['toPay'] = 0
                    grand_total['paid'] = 0
                    grand_total['AC'] = 0
                    grand_total['grand_freight'] = 0
                    grand_total['grand_hamali'] = 0
                    grand_total['grand_door_charge'] = 0
                    grand_total['grand_st_charge'] = 0
                    grand_total['grand_total'] = 0

                    # Aggregate data based on pay_status
                    statuses = ['toPay', 'paid', 'AC']
                    for status in statuses:
                        status_trips = trips.filter(pay_status=status)
                        summary[status]['freight'] = status_trips.aggregate(total=Sum('freight'))['total'] or 0
                        summary[status]['hamali'] = status_trips.aggregate(total=Sum('hamali'))['total'] or 0
                        summary[status]['st_charge'] = status_trips.aggregate(total=Sum('st_charge'))['total'] or 0
                        summary[status]['door_charge'] = status_trips.aggregate(total=Sum('door_charge'))['total'] or 0
                        summary[status]['total_cost'] = status_trips.aggregate(total=Sum('total_cost'))['total'] or 0

                        # Update grand totals
                        grand_total[status] = summary[status]['total_cost']
                        grand_total['grand_freight'] += summary[status]['freight']
                        grand_total['grand_hamali'] += summary[status]['hamali']
                        grand_total['grand_st_charge'] += summary[status]['st_charge']
                        grand_total['grand_door_charge'] += summary[status]['door_charge']
                        grand_total['grand_total'] += summary[status]['total_cost']

                    # Calculate the total value using only the first row
                    if trips.exists():
                        first_trip = trips.first()
                        total_ltr_value = float(
                            first_trip.LTRate * first_trip.Ltr) if first_trip.LTRate and first_trip.Ltr else 0.0
                        total_adv_given = float(first_trip.AdvGiven) if first_trip.AdvGiven else 0.0
                        total_commission = float(first_trip.commission) if first_trip.commission else 0.0
                        total_value = total_ltr_value + total_adv_given + total_commission
                    else:
                        total_value = 0.0

        except ObjectDoesNotExist:
            trips = TripSheetTemp.objects.none()

    return render(request, 'staffTripSheetList.html', {
        'trips': trips,
        'total_value': total_value,
        'total_qty': total_qty,
        'grand_total': grand_total,
        'summary': summary
    })

def staffViewTripSheetList(request):
    grouped_trips = []
    uid = request.session.get('username')

    if uid:
        try:
            branch = Staff.objects.get(staffPhone=uid)
            user_branch = branch.Branch

            if request.method == 'POST':
                date = request.POST.get('t3')

                if date:
                    # Group by VehicalNo and Date, and annotate with count
                    grouped_trips = (
                        TripSheetPrem.objects
                        .filter(Date=date, branch=user_branch)
                        .values('VehicalNo', 'Date')
                        .annotate(trip_count=Count('id'))
                    )

        except ObjectDoesNotExist:
            grouped_trips = []

    return render(request, 'staffViewTripSheetList.html', {
        'grouped_trips': grouped_trips
    })

def staffprintTripSheetList(request, vehical_no, date):
    trips = []
    total_value = 0
    total_qty = 0
    grand_total = {
        'toPay': 0,
        'paid': 0,
        'AC': 0,
        'grand_freight': 0,
        'grand_hamali': 0,
        'grand_door_charge': 0,
        'grand_st_charge': 0,
        'grand_total': 0
    }
    summary = {
        'toPay': {'freight': 0, 'hamali': 0, 'st_charge': 0, 'door_charge': 0, 'total_cost': 0},
        'paid': {'freight': 0, 'hamali': 0, 'st_charge': 0, 'door_charge': 0, 'total_cost': 0},
        'AC': {'freight': 0, 'hamali': 0, 'st_charge': 0, 'door_charge': 0, 'total_cost': 0}
    }

    uid = request.session.get('username')

    if uid:
        try:
            branch = Staff.objects.get(staffPhone=uid)
            user_branch = branch.Branch

            # Filter trips based on VehicleNo, Date, and branch
            trips = TripSheetPrem.objects.filter(
                VehicalNo=vehical_no,
                Date=date,
                branch=user_branch
            )

            # Calculate total quantity
            total_qty = trips.aggregate(total_qty=Sum('qty'))['total_qty'] or 0

            # Aggregate data based on pay_status
            statuses = ['toPay', 'paid', 'AC']
            for status in statuses:
                status_trips = trips.filter(pay_status=status)
                summary[status]['freight'] = status_trips.aggregate(total=Sum('freight'))['total'] or 0
                summary[status]['hamali'] = status_trips.aggregate(total=Sum('hamali'))['total'] or 0
                summary[status]['st_charge'] = status_trips.aggregate(total=Sum('st_charge'))['total'] or 0
                summary[status]['door_charge'] = status_trips.aggregate(total=Sum('door_charge'))['total'] or 0
                summary[status]['total_cost'] = status_trips.aggregate(total=Sum('total_cost'))['total'] or 0

                # Update grand totals
                grand_total[status] = summary[status]['total_cost']
                grand_total['grand_freight'] += summary[status]['freight']
                grand_total['grand_hamali'] += summary[status]['hamali']
                grand_total['grand_st_charge'] += summary[status]['st_charge']
                grand_total['grand_door_charge'] += summary[status]['door_charge']
                grand_total['grand_total'] += summary[status]['total_cost']

            # Calculate the total value using the first row
            if trips.exists():
                first_trip = trips.first()
                total_ltr_value = float(first_trip.LTRate * first_trip.Ltr) if first_trip.LTRate and first_trip.Ltr else 0.0
                total_adv_given = float(first_trip.AdvGiven) if first_trip.AdvGiven else 0.0
                total_commission = float(first_trip.commission) if first_trip.commission else 0.0
                total_value = total_ltr_value + total_adv_given + total_commission
            else:
                total_value = 0.0

        except Branch.DoesNotExist:
            trips = TripSheetPrem.objects.none()  # Handle case where Branch does not exist

    return render(request, 'printTripSheetList.html', {
        'trips': trips,
        'total_value': total_value,
        'total_qty': total_qty,
        'grand_total': grand_total,
        'summary': summary
    })

def branchExpenses(request):
    return render(request, 'branchExpenses.html')
def savebranchExpenses(request):
    if request.method == 'POST':
        uid = request.session.get('username')
        if uid:
            try:
                branch = Branch.objects.get(email=uid)
                branchname = branch.companyname
                username = branch.headname

                # Parse and validate date
                date_str = request.POST.get('date')
                try:
                    date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    print("Invalid date format.")  # Debugging statement
                    return redirect('branchExpenses')

                # Parse and validate amount
                amount = request.POST.get('amt')
                reason = request.POST.get('reason')

                Expenses.objects.create(
                    Date=date,
                    Reason=reason,
                    Amount=amount,
                    username=username,
                    branch=branchname
                )
            except Branch.DoesNotExist:
                print("Branch does not exist.")  # Debugging statement
        else:
            print("No username found in session.")  # Debugging statement

        return redirect('branchExpenses')  # Replace with your desired success URL

    return render(request, 'branchExpenses.html')

def adminExpenses(request):
    return render(request, 'adminExpenses.html')
def saveadminExpenses(request):
    if request.method == 'POST':
        uid = request.session.get('username')
        if uid:
            try:
                branch = Login.objects.get(username=uid)
                branchname = branch.utype
                username = branch.name

                # Parse and validate date
                date_str = request.POST.get('date')
                try:
                    date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    print("Invalid date format.")  # Debugging statement
                    return redirect('adminExpenses')

                # Parse and validate amount
                amount = request.POST.get('amt')
                reason = request.POST.get('reason')

                Expenses.objects.create(
                    Date=date,
                    Reason=reason,
                    Amount=amount,
                    username=username,
                    branch=branchname
                )
            except Branch.DoesNotExist:
                print("Branch does not exist.")  # Debugging statement
        else:
            print("No username found in session.")  # Debugging statement

        return redirect('adminExpenses')  # Replace with your desired success URL

    return render(request, 'adminExpenses.html')


def fetch_consignments(request):
    consignments = AddConsignment.objects.all()
    consignments_data = [
        {
            'id': consignment.id,
            'track_id': consignment.track_id,
            'sender_name': consignment.sender_name,
            'receiver_name': consignment.receiver_name,
        }
        for consignment in consignments
    ]
    return JsonResponse(consignments_data, safe=False)

def fetch_details(request):
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    driver_id = request.GET.get('driver_id')
    consignor_id = request.GET.get('consignor_id')
    consignee_id = request.GET.get('consignee_id')

    # Filter based on the provided parameters
    consignments = AddConsignment.objects.all()


    if consignor_id:
        consignments = consignments.filter(sender_name__icontains=consignor_id)
    if consignee_id:
        consignments = consignments.filter(receiver_name__icontains=consignee_id)

    # Prepare the data for JSON response
    data = [
        {
            'track_id': consignment.track_id,
            'sender_name': consignment.sender_name,
            'receiver_name': consignment.receiver_name,
            'desc_product': consignment.desc_product,
            'pieces': consignment.pieces,
            'total_cost': consignment.total_cost,
        }
        for consignment in consignments
    ]

    return JsonResponse({'data': data})


def payment_history(request):
    return render(request, 'payment_history.html')

def credit(request):
    credit = Account.objects.all()
    return render(request, 'credit.html', {'credit': credit})

@csrf_exempt
def fetch_balance(request):
    if request.method == 'GET':
        sender_name = request.GET.get('sender_name')
        if sender_name:
            accounts = Account.objects.filter(sender_name=sender_name)
            if accounts.exists():
                latest_account = accounts.latest('Date')  # Get the latest record by date
                return JsonResponse({'balance': latest_account.Balance})
            return JsonResponse({'balance': '0'})  # Default if no records found
        return JsonResponse({'status': 'error', 'message': 'Sender name is required'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@csrf_exempt
def submit_credit(request):
    if request.method == 'POST':
        uid = request.session.get('username')

        consignor_name = request.POST.get('consignor_name')
        credit_amount = request.POST.get('credit_amount')
        now = datetime.now()
        if consignor_name and credit_amount:
            try:

                branch = Staff.objects.get(staffPhone=uid)
                username = branch.staffname
                # Fetch all matching records
                accounts = Account.objects.filter(sender_name=consignor_name)

                if accounts.exists():
                    # Get the latest account for calculating the new balance
                    latest_account = accounts.latest('Date')  # Assuming you want to get the latest record

                    # Calculate the new balance
                    new_balance = float(latest_account.Balance) - float(credit_amount)

                    # Create a new record with updated balance
                    new_account = Account(
                        sender_name=consignor_name,
                        credit=credit_amount,
                        debit='0',
                        TrType="ReCap",
                        particulars="Credited",# Set debit to zero
                        Balance=str(new_balance),  # Set the new balance
                        Date=now,  # Use the date of the latest record or set to current date
                        headname=username
                    )
                    new_account.save()

                    return JsonResponse({'status': 'success'})
                else:
                    return JsonResponse({'status': 'error', 'message': 'No account found with the given sender name'})

            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)})

        return JsonResponse({'status': 'error', 'message': 'Invalid data'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})



def credit_print(request):
    credit = Account.objects.all()
    return render(request, 'credit_print.html', {'credit': credit})

def fetch_account_details(request):
    sender_name = request.GET.get('sender_name')
    accounts = Account.objects.filter(sender_name=sender_name).values(
        'Date', 'track_number', 'TrType', 'particulars', 'debit', 'credit', 'Balance'
    )
    return JsonResponse({'accounts': list(accounts)})

@csrf_exempt
def fetch_name(request):
    if request.method == 'GET':
        sender_name = request.GET.get('sender_name')
        if sender_name:
            accounts = Account.objects.filter(sender_name=sender_name)
            if accounts.exists():
                latest_record = accounts.latest('Date')
                return JsonResponse({'sender_name': latest_record.sender_name})
            return JsonResponse({'sender_name': sender_name})
        return JsonResponse({'status': 'error', 'message': 'Sender name is required'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

def branchPaymenyHistory(request):
    return render(request,'branchPaymenyHistory.html')

def branchcredit(request):
    credit = Account.objects.all()
    return render(request, 'credit.html', {'credit': credit})

@csrf_exempt
def branchfetch_balance(request):
    if request.method == 'GET':
        sender_name = request.GET.get('sender_name')
        if sender_name:
            accounts = Account.objects.filter(sender_name=sender_name)
            if accounts.exists():
                latest_account = accounts.latest('Date')  # Get the latest record by date
                return JsonResponse({'balance': latest_account.Balance})
            return JsonResponse({'balance': '0'})  # Default if no records found
        return JsonResponse({'status': 'error', 'message': 'Sender name is required'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@csrf_exempt
def branchsubmit_credit(request):
    if request.method == 'POST':
        uid = request.session.get('username')

        consignor_name = request.POST.get('consignor_name')
        credit_amount = request.POST.get('credit_amount')
        now = datetime.now()
        if consignor_name and credit_amount:
            try:

                branch = Staff.objects.get(staffPhone=uid)
                username = branch.staffname
                # Fetch all matching records
                accounts = Account.objects.filter(sender_name=consignor_name)

                if accounts.exists():
                    # Get the latest account for calculating the new balance
                    latest_account = accounts.latest('Date')  # Assuming you want to get the latest record

                    # Calculate the new balance
                    new_balance = float(latest_account.Balance) - float(credit_amount)

                    # Create a new record with updated balance
                    new_account = Account(
                        sender_name=consignor_name,
                        credit=credit_amount,
                        debit='0',
                        TrType="ReCap",
                        particulars="Credited",# Set debit to zero
                        Balance=str(new_balance),  # Set the new balance
                        Date=now,  # Use the date of the latest record or set to current date
                        headname=username
                    )
                    new_account.save()

                    return JsonResponse({'status': 'success'})
                else:
                    return JsonResponse({'status': 'error', 'message': 'No account found with the given sender name'})

            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)})

        return JsonResponse({'status': 'error', 'message': 'Invalid data'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})



def branchcredit_print(request):
    credit = Account.objects.all()
    return render(request, 'credit_print.html', {'credit': credit})

def branchfetch_account_details(request):
    sender_name = request.GET.get('sender_name')
    accounts = Account.objects.filter(sender_name=sender_name).values(
        'Date', 'track_number', 'TrType', 'particulars', 'debit', 'credit', 'Balance'
    )
    return JsonResponse({'accounts': list(accounts)})
