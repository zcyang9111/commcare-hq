from django.conf import settings
from django.test import TestCase

from nose.tools import assert_in

from corehq.motech.const import BASIC_AUTH
from corehq.motech.models import ConnectionSettings

from ..models import FormRepeater, SQLRepeaterStub, get_all_repeater_types
from ..repeater_generators import FormRepeaterXMLPayloadGenerator


def test_get_all_repeater_types():
    types = get_all_repeater_types()
    for cls in settings.REPEATER_CLASSES:
        name = cls.split('.')[-1]
        assert_in(name, types)


class RepeaterConnectionSettingsTests(TestCase):

    def setUp(self):
        self.rep = FormRepeater(
            domain="greasy-spoon",
            url="https://spam.example.com/api/",
            auth_type=BASIC_AUTH,
            username="terry",
            password="Don't save me decrypted!",
            notify_addresses_str="admin@example.com",
            format=FormRepeaterXMLPayloadGenerator.format_name,
        )

    def tearDown(self):
        if self.rep.connection_settings_id:
            ConnectionSettings.objects.filter(
                pk=self.rep.connection_settings_id
            ).delete()
        self.rep.delete()

    def test_create_connection_settings(self):
        self.assertIsNone(self.rep.connection_settings_id)
        conn = self.rep.connection_settings

        self.assertIsNotNone(self.rep.connection_settings_id)
        self.assertEqual(conn.name, self.rep.url)
        self.assertEqual(self.rep.plaintext_password, conn.plaintext_password)
        # rep.password was saved decrypted; conn.password is not:
        self.assertNotEqual(self.rep.password, conn.password)


class TestSQLRepeatRecordOrdering(TestCase):

    def setUp(self):
        self.couch_repeater = FormRepeater(
            domain='eden',
            url='https://spam.example.com/api/',
        )
        self.couch_repeater.save()
        self.sql_repeater = SQLRepeaterStub.objects.create(
            domain='eden',
            couch_id=self.couch_repeater.get_id,
        )
        self.sql_repeater.repeat_records.create(
            domain=self.sql_repeater.domain,
            payload_id='eve',
            registered_at='1970-02-01',
        )

    def tearDown(self):
        self.sql_repeater.delete()
        self.couch_repeater.delete()

    def test_earlier_record_created_later(self):
        self.sql_repeater.repeat_records.create(
            domain=self.sql_repeater.domain,
            payload_id='lilith',
            # If Unix time starts on 1970-01-01, then I guess 1970-01-06
            # is Unix Rosh Hashanah, the sixth day of Creation, the day
            # [Lilith][1] and Adam were created from clay.
            # [1] https://en.wikipedia.org/wiki/Lilith
            registered_at='1970-01-06',
        )
        repeat_records = self.sql_repeater.repeat_records.all()
        self.assertEqual(repeat_records[0].payload_id, 'lilith')
        self.assertEqual(repeat_records[1].payload_id, 'eve')

    def test_later_record_created_later(self):
        self.sql_repeater.repeat_records.create(
            domain=self.sql_repeater.domain,
            payload_id='cain',
            registered_at='1995-01-06',
        )
        repeat_records = self.sql_repeater.repeat_records.all()
        self.assertEqual(repeat_records[0].payload_id, 'eve')
        self.assertEqual(repeat_records[1].payload_id, 'cain')
