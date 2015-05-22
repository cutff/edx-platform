"""
This module is essentially a broker to xmodule/tabs.py -- it was originally introduced to
perform some LMS-specific tab display gymnastics for the Entrance Exams feature
"""
from django.conf import settings
from django.utils.translation import ugettext as _

from courseware.entrance_exams import user_must_complete_entrance_exam
from openedx.core.djangoapps.course_views.course_views import CourseViewTypeManager, CourseViewType
from xmodule.tabs import CourseTab, CourseTabList, CourseViewTab


class SyllabusCourseView(CourseViewType):
    """
    A tab for the course syllabus.
    """
    name = 'syllabus'
    title = _('Syllabus')
    priority = 30
    view_name = 'syllabus'
    is_persistent = False

    @classmethod
    def is_enabled(cls, course, django_settings, user=None):  # pylint: disable=unused-argument
        return hasattr(course, 'syllabus_present') and course.syllabus_present


class SingleTextbookTab(CourseTab):
    """
    A tab representing a single textbook.  It is created temporarily when enumerating all textbooks within a
    Textbook collection tab.  It should not be serialized or persisted.
    """
    type = 'single_textbook'
    is_movable = False
    is_collection_item = True
    priority = None

    def to_json(self):
        raise NotImplementedError('SingleTextbookTab should not be serialized.')


class TextbookCourseViewsBase(CourseViewType):
    """
    Abstract class for textbook collection tabs classes.
    """
    # Translators: 'Textbooks' refers to the tab in the course that leads to the course' textbooks
    title = _("Textbooks")
    is_collection = True

    @classmethod
    def is_enabled(cls, course, django_settings, user=None):  # pylint: disable=unused-argument
        return user is None or user.is_authenticated()

    @classmethod
    def items(cls, course):
        """
        A generator for iterating through all the SingleTextbookTab book objects associated with this
        collection of textbooks.
        """
        raise NotImplementedError()


class TextbookCourseViews(TextbookCourseViewsBase):
    """
    A tab representing the collection of all textbook tabs.
    """
    name = 'textbooks'
    priority = None

    @classmethod
    def is_enabled(cls, course, django_settings, user=None):  # pylint: disable=unused-argument
        parent_is_enabled = super(TextbookCourseViews, cls).is_enabled(course, settings, user)
        return django_settings.FEATURES.get('ENABLE_TEXTBOOK') and parent_is_enabled

    @classmethod
    def items(cls, course):
        for index, textbook in enumerate(course.textbooks):
            yield SingleTextbookTab(
                name=textbook.title,
                tab_id='textbook/{0}'.format(index),
                link_func=lambda course, reverse_func, index=index: reverse_func(
                    'book', args=[course.id.to_deprecated_string(), index]
                ),
            )


class PDFTextbookCourseViews(TextbookCourseViewsBase):
    """
    A tab representing the collection of all PDF textbook tabs.
    """
    name = 'pdf_textbooks'
    priority = None

    @classmethod
    def items(cls, course):
        for index, textbook in enumerate(course.pdf_textbooks):
            yield SingleTextbookTab(
                name=textbook['tab_title'],
                tab_id='pdftextbook/{0}'.format(index),
                link_func=lambda course, reverse_func, index=index: reverse_func(
                    'pdf_book', args=[course.id.to_deprecated_string(), index]
                ),
            )


class HtmlTextbookCourseViews(TextbookCourseViewsBase):
    """
    A tab representing the collection of all Html textbook tabs.
    """
    name = 'html_textbooks'
    priority = None

    @classmethod
    def items(cls, course):
        for index, textbook in enumerate(course.html_textbooks):
            yield SingleTextbookTab(
                name=textbook['tab_title'],
                tab_id='htmltextbook/{0}'.format(index),
                link_func=lambda course, reverse_func, index=index: reverse_func(
                    'html_book', args=[course.id.to_deprecated_string(), index]
                ),
            )


def get_course_tab_list(request, course):
    """
    Retrieves the course tab list from xmodule.tabs and manipulates the set as necessary
    """
    user = request.user
    xmodule_tab_list = CourseTabList.iterate_displayable(course, settings, user=user)

    # Now that we've loaded the tabs for this course, perform the Entrance Exam work
    # If the user has to take an entrance exam, we'll need to hide away all of the tabs
    # except for the Courseware and Instructor tabs (latter is only viewed if applicable)
    # We don't have access to the true request object in this context, but we can use a mock
    course_tab_list = []
    for tab in xmodule_tab_list:
        if user_must_complete_entrance_exam(request, user, course):
            # Hide all of the tabs except for 'Courseware'
            # Rename 'Courseware' tab to 'Entrance Exam'
            if tab.type is not 'courseware':
                continue
            tab.name = _("Entrance Exam")
        course_tab_list.append(tab)

    # Add in any dynamic tabs, i.e. those that are not persisted
    course_tab_list += _get_dynamic_tabs(course, user)

    return course_tab_list


def _get_dynamic_tabs(course, user):
    """
    Returns the dynamic tab types for the current user.

    Note: dynamic tabs are those that are not persisted in the course, but are
    instead added dynamically based upon the user's role.
    """
    dynamic_tabs = list()
    for tab_type in CourseViewTypeManager.get_course_view_types():
        if not getattr(tab_type, "is_persistent", True):
            tab = CourseViewTab(tab_type)
            if tab.is_enabled(course, settings, user=user):
                dynamic_tabs.append(tab)
    dynamic_tabs.sort(key=lambda dynamic_tab: dynamic_tab.name)
    return dynamic_tabs
