# -*- coding: utf-8 -*-

from icebergsdk.resources.base import UpdateableIcebergObject


class Application(UpdateableIcebergObject):
    endpoint = 'application'

    def inbox(self):
        return self.get_list("%sinbox/" % self.resource_uri)

    def fetch_secret_key(self):
    	return self.request("%sfetchSecretKey/" % self.resource_uri)["secret_key"]

    def auth_me(self):
        """
        Return the access_token for the current user on this application
        """
        return self.request("%sauth_me/" % self.resource_uri)["access_token"]




class ApplicationCommissionSettings(UpdateableIcebergObject):
    endpoint = 'application_commission_settings'