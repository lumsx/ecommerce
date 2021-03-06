define([
    'jquery',
    'backbone',
    'backbone.super',
    'underscore',
    'views/subscription_form_view',
    'text!templates/subscription_create_edit.html',
    'bootstrap'
],
    function($,
              Backbone,
              BackboneSuper,
              _,
              SubscriptionFormView,
              SubscriptionCreateEditTemplate) {
        'use strict';

        return Backbone.View.extend({
            template: _.template(SubscriptionCreateEditTemplate),
            className: 'subscription-create-edit-view',

            initialize: function(options) {
                // This indicates if we are editing or creating a code.
                this.editing = options.editing;
            },

            remove: function() {
                if (this.formView) {
                    this.formView.remove();
                    this.formView = null;
                }

                this._super(); // eslint-disable-line no-underscore-dangle
            },

            getFormView: function() {
                return this.formView || new SubscriptionFormView({editing: this.editing, model: this.model});
            },

            render: function() {
                var $html,
                    data = this.model.attributes;

                // The form should be instantiated only once.
                this.formView = this.getFormView();

                // Render the basic page layout
                data.editing = this.editing;
                $html = $(this.template(data));

                // Render the form
                this.formView.render();
                $html.find('.subscription-form-outer').html(this.formView.el);

                // Render the complete view
                this.$el.html($html);

                // Activate the tooltips
                this.$el.find('[data-toggle="tooltip"]').tooltip();

                return this;
            }
        });
    }
);
