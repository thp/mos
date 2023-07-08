from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from django.db.models import Sum

from django.db import models
from django.db.models import Q
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.encoding import smart_str, force_str
import smtplib
from django.core.mail import send_mail
# for iButton regex
from django.core.validators import RegexValidator

from easy_thumbnails.fields import ThumbnailerImageField

import string
from django.core.exceptions import ValidationError


country_codes = {
    "AD": 24,
    "AE": 23,
    "AL": 28,
    "AT": 20,
    "AX": 18,
    "AZ": 28,
    "BA": 20,
    "BE": 16,
    "BG": 22,
    "BH": 22,
    "BI": 27,
    "BL": 27,
    "BR": 29,
    "BY": 28,
    "CH": 21,
    "CR": 22,
    "CY": 28,
    "CZ": 24,
    "DE": 22,
    "DK": 18,
    "DO": 28,
    "EE": 20,
    "EG": 29,
    "ES": 24,
    "FI": 18,
    "FO": 18,
    "FR": 27,
    "GB": 22,
    "GE": 22,
    "GF": 27,
    "GG": 22,
    "GI": 23,
    "GL": 18,
    "GP": 27,
    "GR": 27,
    "GT": 28,
    "HR": 21,
    "HU": 28,
    "IE": 22,
    "IL": 23,
    "IM": 22,
    "IQ": 23,
    "IS": 26,
    "IT": 27,
    "JE": 22,
    "JO": 30,
    "KW": 30,
    "KZ": 20,
    "LB": 28,
    "LC": 32,
    "LI": 21,
    "LT": 20,
    "LU": 20,
    "LV": 21,
    "LY": 25,
    "MC": 27,
    "MD": 24,
    "ME": 22,
    "MF": 27,
    "MK": 19,
    "MQ": 27,
    "MR": 27,
    "MT": 31,
    "MU": 30,
    "NC": 27,
    "NL": 18,
    "NO": 15,
    "PF": 27,
    "PK": 24,
    "PL": 28,
    "PM": 27,
    "PS": 29,
    "PT": 25,
    "QA": 29,
    "RE": 27,
    "RO": 24,
    "RS": 22,
    "SA": 24,
    "SC": 31,
    "SD": 18,
    "SE": 24,
    "SI": 19,
    "SK": 24,
    "SM": 27,
    "ST": 25,
    "SV": 28,
    "TF": 27,
    "TL": 23,
    "TN": 24,
    "TR": 26,
    "UA": 29,
    "VA": 22,
    "VG": 24,
    "WF": 27,
    "XK": 20,
    "YT": 27,
    "YY": 34,
    "ZZ": 35,
}

def iban_letters2numbers(iban):
    """Converts all letters to the number equivalent for the IBAN validation algorithm"""
    result = []
    for char in iban:
        if char.isalpha():
            final_char = str(string.ascii_uppercase.find(char.upper()) + 10)
        else:
            final_char = char
        result.append(final_char)
    return "".join(result)

def iban_validate(iban):
    """Validates a given IBAN"""
    if not iban.isalnum():
        raise ValidationError("IBAN can only contain numbers (0-9) and letters (A-Z)!")
    if len(iban) < 4:
        raise ValidationError("IBAN must at least 4 characters long!")
    country_code = iban[:2].upper()
    country_length = country_codes.get(country_code, False)
    if not country_length:
        raise ValidationError(f"IBAN must begin with a valid country code! ({country_code!r} is not known)")
    if not len(iban) == country_length:
        raise ValidationError(f"IBAN is not of correct length for country code {country_code!r}!")
    rearranged_iban = iban[4:] + iban[:4]
    numerized_iban = iban_letters2numbers(rearranged_iban)
    checksum = int(numerized_iban) % 97
    if checksum != 1:
        raise ValidationError("IBAN is not valid!")

class PaymentInfo(models.Model):
    bank_collection_allowed = models.BooleanField(default=False)
    bank_collection_mode = models.ForeignKey(
        'BankCollectionMode',
        on_delete=models.CASCADE,
    )
    bank_account_owner = models.CharField(max_length=200, blank=True)
    bank_account_number = models.CharField(max_length=20, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    bank_code = models.CharField(max_length=20, blank=True)
    bank_account_iban = models.CharField(max_length=34, blank=True, validators=[iban_validate])
    bank_account_bic = models.CharField(max_length=11, blank=True)
    bank_account_mandate_reference = models.CharField(max_length=35, blank=True)
    bank_account_date_of_signing = models.DateField(null=True, blank=True)

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
    )


def get_image_path(self, filename):
    name, ext = filename.rsplit('.', 1)
    return 'userpics/%s.%s' % (self.user.username, ext)


class ContactInfo(models.Model):
    LAZZZOR_RATE_CHOICES = (
        (Decimal('1.00'), "Standard Rate (1.00)"),
        (Decimal('0.50'), "Backer's Rate (0.50)"),
    )

    on_intern_list = models.BooleanField(default=True)
    intern_list_email = models.EmailField(blank=True)

    street = models.CharField(max_length=200)
    postcode = models.CharField(max_length=10)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)

    phone_number = models.CharField(max_length=32, blank=True)
    birthday = models.DateField(null=True, blank=True)

    wiki_name = models.CharField(max_length=50, blank=True, null=True)
    image = ThumbnailerImageField(upload_to=get_image_path, blank=True)

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
    )

    last_email_ok = models.BooleanField(null=True)
    has_active_key = models.BooleanField(default=False)
    has_lazzzor_privileges = models.BooleanField(default=False)

    iButtonValidator = RegexValidator(r"\b[0-9]{2}-[0-9a-zA-Z]{12}\b", "iButton ID entspricht nicht dem Format [0-9]{2}-[0-9a-zA-Z]{12}")
    key_id = models.CharField(max_length=15, blank=True, null=True, validators=[iButtonValidator])

    lazzzor_rate = models.DecimalField(choices=LAZZZOR_RATE_CHOICES, default='1.00',
                                       max_digits=3, decimal_places=2)
    remark = models.TextField(null=True, blank=True)

    def get_membership_fees(self):
        mp_list = MembershipPeriod.objects.filter(user=self.user)
        fees = list(MembershipFee.objects.all())

        for mp in mp_list:
            for month in mp.get_months():
                fee = mp.get_membership_fee(month, fees)
                if fee.amount > 0:
                    yield (month, fee.amount)

    def get_debts(self):
        arrears = sum(f[1] for f in self.get_membership_fees())
        return arrears - self.get_all_payments()

    def get_debts_detailed(self):
        fees = ({"date": f[0], "amount": -f[1], "kind": "membership fee"} for f in self.get_membership_fees())
        payments = ({"date": p.date, "amount": p.amount, "kind": p.method.name} for p in Payment.objects.filter(user=self.user))
        movements = [*fees, *payments]
        movements.sort(key=lambda m: m["date"])

        balance = 0

        for movment in movements:
            balance += movment["amount"]
            movment["balance"] = balance

        movements.reverse()
        return movements

    def get_debt_for_month(self, date_in_month):
        # see if the there is a membership period for the month
        mp_list = MembershipPeriod.objects.filter(Q(begin__lte=date_in_month),
                                                  Q(end__isnull=True) | Q(end__gte=date_in_month),
                                                  user=self.user)

        if not mp_list.exists():
            return 0
        else:
            # find the membership fee for the month and kind
            # of membership and return amount
            mp = mp_list[0]
            fee = mp.kind_of_membership.membershipfee_set.filter(
                Q(start__lte=date_in_month),
                Q(end__isnull=True) | Q(end__gte=date_in_month))[0]

            return fee.amount

    def get_debt_for_this_month(self):
        return self.get_debt_for_month(date.today())

    def get_all_payments(self):
        return Payment.objects.filter(user=self.user).aggregate(Sum('amount'))['amount__sum'] or 0

    def get_date_of_first_join(self):
        mp = MembershipPeriod.objects.filter(user=self.user).order_by('begin').first()
        return mp.begin if mp else None

    def get_current_membership_period(self):
        # FIXME: the order here is wrong, didn't change it since i don't have time to check all implications
        #                    sf - 2010 07 27
        mp = MembershipPeriod.objects.filter(user=self.user)\
            .order_by('begin')[0]
        if mp.end is None:
            return mp
        else:
            return None
        return mp.begin

    def is_active_key_member(self):
        # FIXME: the order here is wrong, didn't change it since i don't have time to check all implications
        #                    sf - 2010 07 27
        mp = MembershipPeriod.objects.filter(user=self.user)\
            .order_by('-begin')[0]
        if mp.end is not None:
            return False

        return self.key_id is not None and self.has_active_key

    def get_wikilink(self):
        wikiname = self.wiki_name or self.user.username

        return u'%sBenutzer:%s' % (settings.HOS_WIKI_URL, wikiname)

    def send_mail(self, subject, body, log_file=None):
        try:
            send_mail(
                subject,
                body,
                settings.HOS_ANNOUNCE_FROM,
                [self.user.email],
                fail_silently=False,
            )
            self.last_email_ok = True
            self.save()
        except smtplib.SMTPException as e:
            if log_file:
                with open(log_file, 'a') as f:
                    f.write('\n\n'+self.user.email)
                    f.write('\n'+repr(e))
            self.last_email_ok = False
            self.save()

def get_mailinglist_members():
    return User.objects.filter(
                Q(membershipperiod__end__isnull=True) |
                Q(membershipperiod__end__gte=datetime.now()))\
                .distinct()


def get_active_members_for(dt):
    return User.objects.filter(
                Q(membershipperiod__begin__lte=dt),
                Q(membershipperiod__end__isnull=True) |
                Q(membershipperiod__end__gte=dt))\
                .distinct()


def get_active_members():
    return get_active_members_for(datetime.now())


def get_active_and_future_members():
    return User.objects.filter(
                Q(membershipperiod__end__isnull=True) |
                Q(membershipperiod__end__gte=datetime.now()))\
                .distinct()


def get_active_membership_months_until(date):
    periods = MembershipPeriod.objects.filter(Q(begin__lte=date))
    res = {}
    for p in periods:
        begin = get_months(p.begin)
        end = get_months(date if p.end is None or p.end > date else p.end)
        nrMonths = end - begin + 1
        kind = p.kind_of_membership.name
        if kind in res:
            res[kind] += nrMonths
        else:
            res[kind] = nrMonths

    return res


def get_months(date):
    return date.month + 12 * date.year


class BankCollectionMode(models.Model):
    name = models.CharField(max_length=20)
    num_month = models.IntegerField()

    def __str__(self):
        return self.name


def get_month_list(cur, end):
    if end is None or end >= date.today():
        end = date.today()

    while cur < end:
        yield cur
        cur = cur + relativedelta(months=1)


class MembershipPeriod(models.Model):
    begin = models.DateField()
    end = models.DateField(null=True, blank=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    kind_of_membership = models.ForeignKey(
        'KindOfMembership',
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return self.user.username

    def get_duration_in_month(self):
        if self.end is None or self.end > date.today():
            end = date.today()
        else:
            end = self.end
        if end < self.begin:
            return 0

        begin = date(self.begin.year, self.begin.month, 1)
        end = date(end.year, end.month, 2)

        month = 0
        while begin < end:
            if begin.month == 12:
                begin = date(begin.year + 1, 1, 1)
            else:
                begin = date(begin.year, begin.month + 1, 1)
            month += 1
        return month

    def get_membership_fee(self, month, fees=None):
        if fees is None:
            fees = list(MembershipFee.objects.all())
        for fee in fees:
            if fee.kind_of_membership_id == self.kind_of_membership_id and fee.start <= month and (fee.end is None or fee.end >= month):
                return fee
        raise Exception(f"could not find a membership fee for month {month} and kind of membership {self.kind_of_membership}")

    def get_months(self):
        return get_month_list(self.begin, self.end)


class MembershipFee(models.Model):
    """
    Defines the membership fee for a certain period of time.
    With this class it is possible to define different amount of
    membership fees for different periods of time and for different
    kind of members, e.g. pupils, unemployees, normal members, ...
    """

    kind_of_membership = models.ForeignKey(
        'KindOfMembership',
        on_delete=models.CASCADE,
    )
    start = models.DateField()
    end = models.DateField(null=True, blank=True)
    amount = models.IntegerField()

    def __str__(self):
        return "%s - %d" % (self.kind_of_membership, self.amount)


class KindOfMembership(models.Model):
    FULL_SPIND_CHOICES = (
        ('no', "0 Spind", 0),
        ('small_1', "1 kleiner Spind", 8),
        ('big_1', "1 großer Spind", 10),
        ('small_2', "2 kleiner Spind", 16),
    )
    SPIND_FEES = {c[0]: c[2] for c in FULL_SPIND_CHOICES}
    SPIND_CHOICES = ((c[0], f"{c[1]} ({c[2]}€)") for c in FULL_SPIND_CHOICES)
    FEE_CATEGORY = (
        ('standard', 'standard'),
        ('free', 'free'),
        ('decreased', 'ermäßigt'),
        ('increased', 'erhöht'),
    )

    name = models.CharField(max_length=30)
    spind = models.CharField(choices=SPIND_CHOICES, max_length=7, default="no")
    fee_category = models.CharField(choices=FEE_CATEGORY, max_length=9, default="standard")

    @property
    def spind_fee(self):
        return self.SPIND_FEES[self.spind]

    def __str__(self):
        return self.name


class PaymentManager(models.Manager):
    def import_smallfile(self, filename, date):
        import csv

        f = open(filename, 'r')
        r = csv.reader(f, delimiter=force_str(';'))

        for line in r:
            if len(line) < 2:
                print(line)
                continue
            try:
                u = User.objects.get(first_name=smart_str(line[0]), last_name=smart_str(line[1]))
            except User.DoesNotExist:
                print(line)
                continue
            except:
                print("exception on line:")
                print(line)
                raise

            sum = line[5]
            try:
                Payment.objects.create(date=date, user=u, amount=sum, method=PaymentMethod.objects.get(name='bank collection'), original_file=filename, original_line=str(line))
            except ValueError:
                print(line)

        f.close()

    # used to import generic payments, including date and payment type (as opposed to import_smallfile)
    def import_generic(self, filename):
        import csv

        f = open(filename, 'r')
        r = csv.reader(f, delimiter=force_str(';'))

        for line in r:
            if len(line) < 9:
                print('malformed:', repr(line))
                continue
            try:
                u = User.objects.get(first_name=smart_str(line[0]), last_name=smart_str(line[1]))
            except User.DoesNotExist:
                print('user not found:', repr(line))
                continue

            sum, date, method = (line[5], line[7], line[8])
            try:
                p = Payment.objects.filter(date=date, amount=sum, user=u)
                if len(p) != 0:
                    print('payment already present:', repr(line))
                    continue
                Payment.objects.create(date=date, user=u, amount=sum, method=PaymentMethod.objects.get(name=method), original_file=filename, original_line=str(line))
                print('created:', repr(line))
            except ValueError:
                print('error creating payment:', repr(line))

        f.close()

    def import_hugefile(self, filename):
        import csv

        f = open(filename, 'r')
        r = csv.reader(f, delimiter=force_str(';'))

        i = 0
        for line in r:
            i += 1
            if not line[0]:
                continue

            if line[3] in ('sammler', 'Umlaufvermögen:2810 Bank'):
                pms_name = 'bank collection'
            else:
                pms_name = line[3]
            pms = PaymentMethod.objects.filter(name=pms_name)
            if pms:
                pm = pms[0]
            else:
                pm = PaymentMethod.objects.all()[0]

            subject = line[2]

            if '(' in subject and ')' in subject:
                list_str = subject.split('(')[1].split(')')[0]
                if list_str == '280':
                    list = [subject.split('(')[0]]
                else:
                    list = list_str.split(',')
            else:
                list = [subject]

            sum = line[5] if line[5] else '-'+line[4] if line[4] else '0'

            sum = sum.replace(',', '.')

            try:
                sum = Decimal(sum) / len(list)
            except Exception as e:
                print(e)
                print(line)
                continue

            for name in list:
                fragments = name.split(' ')

#                if line[0] == '2007-10-02':
#                    print name, fragments

                if fragments[0] == '':
                    fragments = fragments[1:]

                if len(fragments) == 0:
                    print('aaaaaaaaaahhh!!')
                    continue

                if fragments[0] == 'fehlgeschlagen':
                    fragments = fragments[1:]

                if 'ckzahlung' in fragments[0]:
                    fragments = fragments[1:]

                if fragments[0] == 'Ewald-Oliver':
                    fragments[0] = 'Oliver'

                if len(fragments) > 1:
                    if fragments[1] in ('Sirek', 'Siereck'):
                        fragments[1] = 'Sierek'

                    if fragments[1] == 'Eckhardt':
                        fragments[1] = 'Eckardt'

                    if fragments[1] == 'Grenzfurtner':
                        fragments[1] = 'Grenzfurthner'

                    if fragments[1] in ('Berg',):  # Berg San, Leo Findeisen
                        fragments = fragments[1:]

                    if fragments[1] in ('Leo',):
                        fragments = [fragments[0], fragments[2]]

                    if fragments[0] == 'Schreiner':
                        fragments = [fragments[1], fragments[0]]

                    if fragments[1] == 'Manztos':
                        fragments[1] = 'Mantzos'

                    if len(fragments) > 2 and fragments[2]:
                        if fragments[2] == 'Laub':
                            fragments = fragments[1:]

                if(len(fragments) > 1):
                    u = User.objects.filter(first_name__iexact=fragments[0], last_name__iexact=fragments[1])
                    if len(u) != 1:
                        print(u, fragments)
                    else:
                        Payment.objects.create(user=u[0], amount=sum,
                                               date=line[0], method=pm,
                                               original_line=str(line),
                                               original_file=filename,
                                               original_lineno=i)

                else:
                    print('no user found for')
                    print(line)
        
        f.close()

class PaymentMethod(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Payment(models.Model):
    amount = models.FloatField()
    comment = models.CharField(max_length=200, blank=True)
    date = models.DateField()
    method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
    )
    original_line = models.TextField(blank=True)
    original_file = models.CharField(max_length=200, null=True)
    original_lineno = models.IntegerField(blank=True, null=True)

    objects = PaymentManager()

    def __str__(self):
        return u"%s, %s, %s, %s" % (self.date, self.amount, self.user.username, self.method.name)

    class Meta:
        ordering = ['date']


class MailinglistMail(models.Model):
    email = models.EmailField()
    on_intern_list = models.BooleanField(default=True)

    def __str__(self):
        return self.email
