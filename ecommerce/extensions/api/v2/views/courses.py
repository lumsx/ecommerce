"""HTTP endpoints for interacting with courses."""
import waffle
from django.db.models import Prefetch
from oscar.core.loading import get_model
from rest_framework import status
from rest_framework.decorators import detail_route
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ecommerce.core.constants import COURSE_ID_REGEX
from ecommerce.courses.models import Course
from ecommerce.extensions.api import serializers
from ecommerce.extensions.api.v2.views import NonDestroyableModelViewSet
from ecommerce.extensions.edly_ecommerce_app.helpers import is_valid_site_course
from ecommerce.extensions.edly_ecommerce_app.permissions import IsAdminOrCourseCreator

Product = get_model('catalogue', 'Product')
ProductAttributeValue = get_model('catalogue', 'ProductAttributeValue')


class CourseViewSet(NonDestroyableModelViewSet):
    product_attribute_value_prefetch = Prefetch(
        'products__attribute_values',
        queryset=ProductAttributeValue.objects.select_related('attribute').all()
    )
    products_prefetch = Prefetch(
        'products',
        queryset=Product.objects.select_related('parent__product_class').all()
    )
    lookup_value_regex = COURSE_ID_REGEX
    serializer_class = serializers.CourseSerializer
    permission_classes = (IsAuthenticated, IsAdminOrCourseCreator,)

    def get_queryset(self):
        site_configuration = self.request.site.siteconfiguration
        return Course.objects.filter(partner=site_configuration.partner).prefetch_related(
            self.products_prefetch, self.product_attribute_value_prefetch, 'products__stockrecords'
        )

    def list(self, request, *args, **kwargs):
        """
        List all courses.
        ---
        parameters:
            - name: include_products
              description: Indicates if the related products should be included in the response.
              required: false
              type: boolean
              paramType: query
              multiple: false
        """
        return super(CourseViewSet, self).list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        site_configuration = request.site.siteconfiguration
        course = Course.objects.create(
            id=request.data['id'],
            name=request.data['name'],
            partner=site_configuration.partner
        )
        data = serializers.CourseSerializer(course, context={'request': request}).data
        return Response(data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve details for a course.
        ---
        parameters:
            - name: include_products
              description: Indicates if the related products should be included in the response.
              required: false
              type: boolean
              paramType: query
              multiple: false
        """
        course_id = kwargs.get('pk')
        if not is_valid_site_course(course_id, request):
            return Response(
                {
                    'error': 'Course with ID "{course_id}" does not exist for this site.'.format(course_id=course_id)
                },
                status=status.HTTP_404_NOT_FOUND
            )
        return super(CourseViewSet, self).retrieve(request, *args, **kwargs)

    def get_serializer_context(self):
        context = super(CourseViewSet, self).get_serializer_context()
        context['include_products'] = bool(self.request.GET.get('include_products', False)) if self.request else False
        return context

    @detail_route(methods=['post'])
    def publish(self, request, pk=None):  # pylint: disable=unused-argument
        """ Publish the course to LMS. """
        course = self.get_object()
        published = False
        msg = 'Course [{course_id}] was not published to LMS ' \
              'because the switch [publish_course_modes_to_lms] is disabled.'

        if waffle.switch_is_active('publish_course_modes_to_lms'):
            published = course.publish_to_lms()
            if published:
                msg = 'Course [{course_id}] was successfully published to LMS.'
            else:
                msg = 'An error occurred while publishing [{course_id}] to LMS.'

        return Response({'status': msg.format(course_id=course.id)},
                        status=status.HTTP_200_OK if published else status.HTTP_500_INTERNAL_SERVER_ERROR)
