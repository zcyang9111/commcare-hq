from django.conf.urls.defaults import patterns
from django.template.defaulttags import url

urlpatterns = patterns('corehq.apps.app_manager.views',
    (r'view/(?P<app_id>\w+)/$',                                             'view_app'),
    (r'view/$',                                                             'default'),

    (r'new_module/(?P<app_id>\w+)/$',                                       'new_module'),
    (r'new_app/$',                                                          'new_app'),
    (r'new_form/(?P<app_id>\w+)/(?P<module_id>\w+)/$',                      'new_form'),

    (r'delete_app/(?P<app_id>\w+)/$',                                       'delete_app'),
    (r'delete_module/(?P<app_id>\w+)/(?P<module_id>\w+)/$',                 'delete_module'),
    (r'delete_form/(?P<app_id>\w+)/(?P<module_id>\w+)/(?P<form_id>\w+)/$',  'delete_form'),

    (r'edit_form_attr/(?P<app_id>\w+)/(?P<module_id>\w+)/(?P<form_id>\w+)/(?P<attr>\w+)/$',
                                                                            'edit_form_attr'),

    (r'edit_module_detail/(?P<app_id>\w+)/(?P<module_id>\w+)/$',            'edit_module_detail'),
    (r'edit_module_attr/(?P<app_id>\w+)/(?P<module_id>\w+)/(?P<attr>\w+)/$','edit_module_attr'),
    (r'delete_module_detail/(?P<app_id>\w+)/(?P<module_id>\w+)/$',          'delete_module_detail'),

    (r'edit_app_lang/(?P<app_id>\w+)/$',                                    'edit_app_lang'),
    (r'delete_app_lang/(?P<app_id>\w+)/$',                                  'delete_app_lang'),
    (r'edit_app_attr/(?P<app_id>\w+)/(?P<attr>\w+)/$',                      'edit_app_attr'),

    (r'swap/(?P<app_id>\w+)/(?P<key>\w+)/$',                                'swap'),

    (r'download/(?P<app_id>\w+)/$',                                         'download_index'),
    (r'download/(?P<app_id>\w+)/suite.xml$',                                'download_suite'),
    (r'download/(?P<app_id>\w+)/profile.xml$',                              'download_profile'),
    (r'download/(?P<app_id>\w+)/(?P<lang>\w+)/app_strings.txt$',            'download_app_strings'),
    (r'download/(?P<app_id>\w+)/m(?P<module_id>\d+)/f(?P<form_id>\d+).xml$',
                                                                            'download_xform'),
    (r'download/(?P<app_id>\w+)/CommCare.jad',                              'download_jad'),
    (r'download/(?P<app_id>\w+)/CommCare_raw.jar',                          'download_jar'),
    (r'download/(?P<app_id>\w+)/CommCare.jar',                              'download_zipped_jar'),

    (r'save/(?P<app_id>\w+)/$',                                             'save_copy'),
    (r'revert/(?P<app_id>\w+)/$',                                           'revert_to_copy'),
    (r'delete_copy/(?P<app_id>\w+)/$',                                      'delete_copy'),
)