"""
Tabs for courseware.
"""
from openedx.core.lib.plugins.api import PluginManager
from xmodule.tabs import CourseTab, key_checker, need_name, link_value_func, link_reverse_func
from courseware.access import has_access
from student.models import CourseEnrollment
from ccx.overrides import get_current_ccx

_ = lambda text: text


# Stevedore extension point namespaces
COURSE_VIEW_TYPE_NAMESPACE = 'openedx.course_view_type'


class CourseViewType(object):
    """
    Base class of all course view type plugins.
    """
    name = None
    title = None
    priority = None
    view_name = None
    is_movable = True
    is_persistent = False
    is_hideable = False

    @classmethod
    def is_enabled(cls, course, django_settings, user=None):  # pylint: disable=unused-argument
        """Returns true if this course view is enabled in the course.

        Args:
            course (CourseDescriptor): the course using the feature
            settings (dict): a dict of configuration settings

            user (User): the user interacting with the course
        """
        raise NotImplementedError()

    @classmethod
    def validate(cls, tab_dict, raise_error=True):  # pylint: disable=unused-argument
        """
        Validates the given dict-type `tab_dict` object to ensure it contains the expected keys.
        This method should be overridden by subclasses that require certain keys to be persisted in the tab.
        """
        return True


class CourseViewTypeManager(PluginManager):
    """
    Manager for all of the course view types that have been made available.

    All course view types should implement `CourseViewType`.
    """
    NAMESPACE = COURSE_VIEW_TYPE_NAMESPACE

    @classmethod
    def get_course_view_types(cls):
        """
        Returns the list of available course view types in their canonical order.
        """
        def compare_course_view_types(first_type, second_type):
            """Compares two course view types, for use in sorting."""
            first_priority = first_type.priority
            second_priority = second_type.priority
            if not first_priority == second_priority:
                if not first_priority:
                    return -1
                elif not second_priority:
                    return 1
                else:
                    return first_priority - second_priority
            first_name = first_type.name
            second_name = second_type.name
            if first_name < second_name:
                return -1
            elif first_name == second_name:
                return 0
            else:
                return 1
        course_view_types = CourseViewTypeManager.get_available_plugins().values()
        course_view_types.sort(cmp=compare_course_view_types)
        return course_view_types


def is_user_staff(course, user):
    """
    Returns true if the user is staff in the specified course, or globally.
    """
    return has_access(user, 'staff', course, course.id)


def is_user_enrolled_or_staff(course, user):
    """
    Returns true if the user is enrolled in the specified course,
    or if the user is staff.
    """
    return is_user_staff(course, user) or CourseEnrollment.is_enrolled(user, course.id)


class AuthenticatedCourseTab(CourseTab):
    """
    Abstract class for tabs that can be accessed by only authenticated users.
    """
    def is_enabled(self, course, settings, user=None):
        return not user or user.is_authenticated()


class EnrolledOrStaffTab(AuthenticatedCourseTab):
    """
    Abstract class for tabs that can be accessed by only users with staff access
    or users enrolled in the course.
    """
    def is_enabled(self, course, settings, user=None):  # pylint: disable=unused-argument
        if not user:
            return True
        return is_user_enrolled_or_staff(course, user)


class StaffTab(AuthenticatedCourseTab):
    """
    Abstract class for tabs that can be accessed by only users with staff access.
    """
    def is_enabled(self, course, settings, user=None):  # pylint: disable=unused-argument
        return not user or is_user_staff(course, user)


class DiscussionTab(EnrolledOrStaffTab):
    """
    A tab only for the new Berkeley discussion forums.
    """

    type = 'discussion'
    name = 'discussion'
    priority = None

    def __init__(self, tab_dict=None):
        super(DiscussionTab, self).__init__(
            # Translators: "Discussion" is the title of the course forum page
            name=tab_dict['name'] if tab_dict else _('Discussion'),
            tab_id=self.type,
            link_func=link_reverse_func('django_comment_client.forum.views.forum_form_discussion'),
        )

    def is_enabled(self, course, settings, user=None):
        if settings.FEATURES.get('CUSTOM_COURSES_EDX', False):
            if get_current_ccx():
                return False
        super_can_display = super(DiscussionTab, self).is_enabled(course, settings, user=user)
        return settings.FEATURES.get('ENABLE_DISCUSSION_SERVICE') and super_can_display

    @classmethod
    def validate(cls, tab_dict, raise_error=True):
        return super(DiscussionTab, cls).validate(tab_dict, raise_error) and need_name(tab_dict, raise_error)


class LinkTab(CourseTab):
    """
    Abstract class for tabs that contain external links.
    """
    link_value = ''

    def __init__(self, name, tab_id, link_value):
        self.link_value = link_value
        super(LinkTab, self).__init__(
            name=name,
            tab_id=tab_id,
            link_func=link_value_func(self.link_value),
        )

    def __getitem__(self, key):
        if key == 'link':
            return self.link_value
        else:
            return super(LinkTab, self).__getitem__(key)

    def __setitem__(self, key, value):
        if key == 'link':
            self.link_value = value
        else:
            super(LinkTab, self).__setitem__(key, value)

    def to_json(self):
        to_json_val = super(LinkTab, self).to_json()
        to_json_val.update({'link': self.link_value})
        return to_json_val

    def __eq__(self, other):
        if not super(LinkTab, self).__eq__(other):
            return False
        return self.link_value == other.get('link')

    @classmethod
    def validate(cls, tab_dict, raise_error=True):
        return super(LinkTab, cls).validate(tab_dict, raise_error) and key_checker(['link'])(tab_dict, raise_error)


class ExternalDiscussionTab(LinkTab):
    """
    A tab that links to an external discussion service.
    """

    type = 'external_discussion'
    name = 'external_discussion'
    priority = None

    def __init__(self, tab_dict=None, link_value=None):
        super(ExternalDiscussionTab, self).__init__(
            # Translators: 'Discussion' refers to the tab in the courseware that leads to the discussion forums
            name=_('Discussion'),
            tab_id='discussion',
            link_value=tab_dict['link'] if tab_dict else link_value,
        )


class ExternalLinkTab(LinkTab):
    """
    A tab containing an external link.
    """
    type = 'external_link'
    name = 'external_link'
    priority = None

    def __init__(self, tab_dict):
        super(ExternalLinkTab, self).__init__(
            name=tab_dict['name'],
            tab_id=None,  # External links are never active.
            link_value=tab_dict['link'],
        )


class StaticTab(CourseTab):
    """
    A custom tab.
    """
    type = 'static_tab'
    name = 'static_tab'
    priority = None

    @classmethod
    def validate(cls, tab_dict, raise_error=True):
        return (super(StaticTab, cls).validate(tab_dict, raise_error)
                and key_checker(['name', 'url_slug'])(tab_dict, raise_error))

    def __init__(self, tab_dict=None, name=None, url_slug=None):
        def link_func(course, reverse_func):
            """ Returns a url for a given course and reverse function. """
            return reverse_func(self.type, args=[course.id.to_deprecated_string(), self.url_slug])

        self.url_slug = tab_dict['url_slug'] if tab_dict else url_slug
        super(StaticTab, self).__init__(
            name=tab_dict['name'] if tab_dict else name,
            tab_id='static_tab_{0}'.format(self.url_slug),
            link_func=link_func,
        )

    def __getitem__(self, key):
        if key == 'url_slug':
            return self.url_slug
        else:
            return super(StaticTab, self).__getitem__(key)

    def __setitem__(self, key, value):
        if key == 'url_slug':
            self.url_slug = value
        else:
            super(StaticTab, self).__setitem__(key, value)

    def to_json(self):
        to_json_val = super(StaticTab, self).to_json()
        to_json_val.update({'url_slug': self.url_slug})
        return to_json_val

    def __eq__(self, other):
        if not super(StaticTab, self).__eq__(other):
            return False
        return self.url_slug == other.get('url_slug')
