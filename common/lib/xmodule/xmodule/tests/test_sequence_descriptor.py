"""
Test suite for use cases involving SequenceDescriptor class
"""
import unittest

from xmodule.seq_module import SequenceDescriptor
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory


class SequenceDescriptorTest(unittest.TestCase):
    """
    Core tests for SequenceDescriptor
    """
    def setUp(self):
        course = CourseFactory.create()
        self.sequence = ItemFactory.create(parent_location=course.location)
        self.assertIsInstance(self.sequence, SequenceDescriptor)

    def test_non_editable_settings(self):
        """
        Test the settings that are marked as "non-editable".
        """
        non_editable_metadata_fields = self.sequence.non_editable_metadata_fields
        self.assertEqual(len(non_editable_metadata_fields), 3)