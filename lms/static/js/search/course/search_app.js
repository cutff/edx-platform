;(function (define) {

define(function() {
    'use strict';

    return function (courseId, SearchRouter, SearchForm, SearchCollection, SearchListView) {

        var router = new SearchRouter();
        var form = new SearchForm();
        var collection = new SearchCollection([], { courseId: courseId });
        var results = new SearchListView({ collection: collection });
        var dispatcher = _.clone(Backbone.Events);

        dispatcher.listenTo(router, 'search', function (query) {
            form.doSearch(query);
        });

        dispatcher.listenTo(form, 'search', function (query) {
            results.showLoadingMessage();
            collection.performSearch(query);
            router.navigate('search/' + query, { replace: true });
        });

        dispatcher.listenTo(form, 'clear', function () {
            collection.cancelSearch();
            results.clear();
            router.navigate('');
        });

        dispatcher.listenTo(results, 'next', function () {
            collection.loadNextPage();
        });

    };

});

})(define || RequireJS.define);