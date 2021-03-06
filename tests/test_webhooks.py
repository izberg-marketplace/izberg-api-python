# -*- coding: utf-8 -*-


from helper import IcebergUnitTestCase, get_api_handler
from helpers.login_utils import IcebergLoginUtils

class WebhookTestCase(IcebergUnitTestCase):
    @classmethod
    def setUpClass(cls):
        cls.my_context_dict = {}
        cls._objects_to_delete = []

        cls.api_handler = get_api_handler()
        IcebergLoginUtils.direct_login_user_1(handler = cls.api_handler)
        # Create an application
        application = cls.api_handler.Application()
        application.name = "test-webhook-app"
        application.contact_user = cls.api_handler.User.me()
        application.save()

        cls.my_context_dict['application'] = application
        cls._objects_to_delete.append(application)

        # Create a merchant
        merchant = cls.api_handler.Store()
        merchant.name = "Test Webhook Merchant"
        merchant.application = application
        merchant.save()

        cls.my_context_dict['merchant'] = merchant
        cls._objects_to_delete.append(merchant)
        cls.my_context_dict['application_token'] = application.auth_me()

    def test_01_create_update_webhook(self):
        """
        Create and update a new_merchant_available webhook
        """
        self.login_user_1()
        self.api_handler.access_token = self.my_context_dict['application_token']
        application = self.my_context_dict['application']
        
        webhook = self.create_webhook(
                    application=application, 
                    event="new_merchant_available",
                    url="http://api.iceberg.technology",
                )
        webhook.url = webhook.get_test_endpoint_url() ## to test update
        webhook.save() 
        self.my_context_dict['webhook_new_merchant'] = webhook


    def test_02_trigger_test_webhook(self):
        """
        Trigger the test option on the webhook
        """
        self.login_user_1()
        self.api_handler.access_token = self.my_context_dict['application_token']

        webhook = self.my_context_dict['webhook_new_merchant']
        webhook.test_trigger()
        webhook_triggers = webhook.wait_for_triggers()
        self.assertEquals(len(webhook_triggers), 1)
        webhook_trigger = webhook_triggers[0]
        self.assertTrue(webhook_trigger.is_test)
        self.assertEquals(webhook_trigger.status, "succeeded")
        

    def test_03_trigger_new_merchant_available(self):
        """
        Test new_merchant_available triggering when creating a new merchant
        """
        self.login_user_1()
        self.api_handler.access_token = self.my_context_dict['application_token']
        
        webhook = self.my_context_dict['webhook_new_merchant']
        new_merchant = self.create_merchant(application=self.my_context_dict['application'])
        webhook_triggers = webhook.wait_for_triggers(number_of_triggers_expected=2)
        self.assertEquals(len(webhook_triggers), 2)
        webhook_trigger = webhook_triggers[0]
        self.assertFalse(webhook_trigger.is_test)
        self.assertEquals(webhook_trigger.status, "succeeded")
        webhook_trigger.fetch() ## fetch detail to get payload
        self.assertEqual(new_merchant.resource_uri, webhook_trigger.payload.get("resource_uri"))


    def test_04_delete_webhook(self):
        """
        Delete the webhook
        """
        self.login_user_1()
        self.api_handler.access_token = self.my_context_dict['application_token']
        webhook = self.my_context_dict['webhook_new_merchant']
        webhook.delete()
        if webhook in self._objects_to_delete:
            ## no need to delete it in tearDownClass if delete succeeded
            self._objects_to_delete.remove(webhook)


    def test_05_create_product_and_webhook(self):
        """
        Create and update a product_offer_updated webhook
        """
        self.login_user_1()
        self.api_handler.access_token = self.my_context_dict['application_token']
        application = self.my_context_dict['application']
        
        webhook_offer = self.create_webhook(
                    application=application,
                    event="product_offer_updated",
                    url="http://api.iceberg.technology",
                    active_merchant_only=False,
                )
        webhook_offer.url = webhook_offer.get_test_endpoint_url()
        webhook_offer.save() ## update

        self.assertEquals(webhook_offer.active_merchant_only, False)

        webhook_product = self.create_webhook(
                    application=application,
                    event="product_updated",
                    url="http://api.iceberg.technology",
                    active_merchant_only=False,
                )
        webhook_product.url = webhook_product.get_test_endpoint_url()
        webhook_product.save() ## update

        self.assertEquals(webhook_product.active_merchant_only, False)
        self.my_context_dict['webhook_offer_updated'] = webhook_offer
        self.my_context_dict['webhook_product_updated'] = webhook_product
        

    def test_06_trigger_product_offer_updated(self):
        """
        Test product_offer_updated/product_updated triggering when updating a product_offer
        """
        self.direct_login_user_1()

        try:
            brand = self.api_handler.Brand.find(1)
        except:
            brand = self.api_handler.Brand()
            brand.name = "Test Brand"
            brand.save()

        product = self.create_product(
                    name = "Test Product",
                    description = "Description of my test product",
                    gender = "W",
                    categories=[50], # chemisier 
                    brand=brand
                )
        self.my_context_dict['product'] = product

        productoffer = self.create_product_offer(
                        product = self.my_context_dict['product'],
                        merchant = self.my_context_dict['merchant'],
                        sku = self.get_random_sku(),
                        price = "90",
                        image_paths = ["./tests/static/image_test.JPEG"]
                    )
        self.my_context_dict['offer'] = productoffer
        productoffer.activate()

        self.assertEquals(productoffer.status, "active")


        productoffer.price = 80
        productoffer.save()

        self.login_user_1()
        self.api_handler.access_token = self.my_context_dict['application_token']

        webhook_offer = self.my_context_dict['webhook_offer_updated']
        webhook_triggers = webhook_offer.wait_for_triggers(number_of_triggers_expected=2)
        self.assertEquals(len(webhook_triggers), 2)
        first_webhook_trigger = webhook_triggers[1]
        first_webhook_trigger.fetch() ## fetch detail to get payload
        second_webhook_trigger = webhook_triggers[0]
        second_webhook_trigger.fetch() ## fetch detail to get payload

        webhook_attempts = first_webhook_trigger.attempts(response_code__gte=200, response_code__lte=205)
        self.assertEquals(len(webhook_attempts), 1)
        self.assertEqual(productoffer.resource_uri, first_webhook_trigger.payload.get("resource_uri"))
        self.assertEqual(first_webhook_trigger.payload.get("updated_attributes"), [u"status"])
        self.assertEqual(first_webhook_trigger.payload.get("status"), u"active")

        webhook_attempts = second_webhook_trigger.attempts(response_code__gte=200, response_code__lte=205)
        self.assertEquals(len(webhook_attempts), 1)
        self.assertEqual(productoffer.resource_uri, second_webhook_trigger.payload.get("resource_uri"))
        self.assertEqual(
            set(second_webhook_trigger.payload.get("updated_attributes")),
            set([u"price", u"price_with_vat", u"price_without_vat"])
        )
        self.assertEqual(float(second_webhook_trigger.payload.get("price")), 80.00)


        webhook_product = self.my_context_dict['webhook_product_updated']
        webhook_triggers = webhook_product.wait_for_triggers(number_of_triggers_expected=2)
        self.assertEquals(len(webhook_triggers), 2)
        webhook_trigger = webhook_triggers[0]
        webhook_trigger.fetch() ## fetch detail to get payload
        webhook_attempts = webhook_trigger.attempts(response_code__gte=200, response_code__lte=205)
        self.assertEquals(len(webhook_attempts), 1)
        self.assertEqual(product.resource_uri, webhook_trigger.payload.get("resource_uri"))
        self.assertEqual(webhook_trigger.payload.get("updated_attributes"), [u"offers"])


    def test_07_trigger_product_offer_updated_2(self):
        """
        Test product_offer_updated/product_updated triggering when removing price (status should go to draft)
        """
        self.login_user_1()
        self.api_handler.access_token = self.my_context_dict['application_token']

        webhook_offer = self.my_context_dict['webhook_offer_updated']
        webhook_product = self.my_context_dict['webhook_product_updated']
        productoffer = self.my_context_dict['offer']
        product = self.my_context_dict['product']

        productoffer.price = 0
        productoffer.save() ## status should go to draft and trigger the webhook

        webhook_triggers = webhook_offer.wait_for_triggers(number_of_triggers_expected=3)
        self.assertEquals(len(webhook_triggers), 3)
        # print "webhook_triggers = %s" % [wt.payload.get("updated_attributes") for wt in webhook_triggers]
        webhook_trigger = webhook_triggers[0]
        webhook_trigger.fetch() ## fetch detail to get payload
        self.assertEqual(productoffer.resource_uri, webhook_trigger.payload.get("resource_uri"))
        self.assertEqual(
            set(webhook_trigger.payload.get("updated_attributes",[])), 
            set([u"status", u"price", u"price_with_vat", u"price_without_vat"])
        )
        self.assertEqual(webhook_trigger.payload.get("status"), u"draft")
        self.assertEqual(float(webhook_trigger.payload.get("price")), 0.)


        webhook_triggers = webhook_product.wait_for_triggers(number_of_triggers_expected=3)
        self.assertEquals(len(webhook_triggers), 3)
        # print "webhook_triggers = %s" % [wt.payload.get("updated_attributes") for wt in webhook_triggers]
        webhook_trigger = webhook_triggers[0]
        webhook_trigger.fetch() ## fetch detail to get payload
        self.assertEqual(product.resource_uri, webhook_trigger.payload.get("resource_uri"))
        self.assertEqual(webhook_trigger.payload.get("updated_attributes"), [u"offers"])


        
