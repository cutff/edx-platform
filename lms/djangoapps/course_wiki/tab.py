"""
These callables are used by django-wiki to check various permissions
a user has on an article.
"""

from django.utils.translation import ugettext as _

from courseware.access import has_access
from courseware.tabs import EnrolledCourseViewType
from student.models import CourseEnrollment


class WikiCourseViewType(EnrolledCourseViewType):
    """
    Defines the Wiki view type that is shown as a course tab.
    """

    name = "wiki"
    title = _('Wiki')
    view_name = "course_wiki"
    is_persistent = True
    is_hideable = True

    @classmethod
    def is_enabled(cls, course, django_settings, user=None):
        """
        Returns true if the wiki is enabled and the specified user is enrolled or has staff access.
        """
        if not super(WikiCourseViewType, cls).is_enabled(course, django_settings, user=user):
            return False
        if not django_settings.WIKI_ENABLED:
            return False
        if not user or course.allow_public_wiki_access:
            return True
        return CourseEnrollment.is_enrolled(user, course.id) or has_access(user, 'staff', course, course.id)
