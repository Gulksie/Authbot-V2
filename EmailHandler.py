# Written by Kayla Gulka, 2022/08/25
# Last modified 2022/08/26

import smtplib, ssl

class EmailHandler:
    def __init__(self):
        self.startEmail()
        
    def startEmail(self):
        # grab login details from file
        with open("loginDetails", 'r') as f:
            loginDetails = f.readlines()

        self.usr, self.passwd = loginDetails[0].split(',')

        # create "ssl" context (which means something, surely, but I'm not a software eng student)
        context = ssl.create_default_context()

        # login to the email and get going
        print("Logging into email...")
        port = 465 # gmail? ssl email port thingy idc
        self.emailServer = smtplib.SMTP_SSL("smtp.gmail.com", port, context=context)

        self.emailServer.login(self.usr, self.passwd)

    def sendEmail(self, code, reciverAddress):
        try:
            print(f"Sending email to {reciverAddress}")
            # we will need to verify somewhere else that reciverAddress is actually a mcmaster email
            # shouldn't be hard
            message = f'''\
    Subject: McMaster Engiqueers Verification

    Hi, your code for verifications in the McMaster Engiqueers discord server is:

    {code}

    This code expiries in 5 minutes!'''
            self.emailServer.sendmail(self.usr, reciverAddress, message)
        except smtplib.SMTPSenderRefused:
            # restart the email thing, then try again
            self.shutdown()
            self.startEmail()
            self.sendMail(code, reciverAddresss)

    def shutdown(self):
        self.emailServer.close()