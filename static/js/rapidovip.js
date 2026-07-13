// Scripts base RapidoVip

(function ($) {

    'use strict';



    // Submenús desktop — clase estable (sin conflicto CSS hover + fadeIn)

    var submenuTimer = null;

    $('.rv-nav > li').each(function () {

        if ($(this).children('.submenu').length) {

            $(this).addClass('has-submenu');

        }

    });



    $('.rv-nav > li.has-submenu').on('mouseenter', function () {

        clearTimeout(submenuTimer);

        $('.rv-nav > li.has-submenu').not(this).removeClass('submenu-open');

        $(this).addClass('submenu-open');

    }).on('mouseleave', function () {

        var $item = $(this);

        submenuTimer = setTimeout(function () {

            $item.removeClass('submenu-open');

        }, 180);

    });



    // Resaltar ítem activo según URL actual

    function normalizePath(path) {

        if (!path) return '/';

        return path.replace(/\/+$/, '') || '/';

    }



    function markActiveNav() {

        var current = normalizePath(window.location.pathname);

        var bestMatch = null;

        var bestLen = 0;



        $('.rv-nav .submenu a, .rv-mobile-nav a[href]').each(function () {

            var href = $(this).attr('href');

            if (!href || href === '#') return;

            var linkPath = normalizePath(href.split('?')[0]);

            if (current === linkPath || (linkPath.length > 1 && current.indexOf(linkPath) === 0)) {

                if (linkPath.length >= bestLen) {

                    bestMatch = this;

                    bestLen = linkPath.length;

                }

            }

        });



        if (bestMatch) {

            $(bestMatch).addClass('active');

            $(bestMatch).closest('.rv-nav > li.has-submenu').addClass('is-current-section');

        }

    }



    markActiveNav();



    // Menú móvil

    var $toggle = $('#rv-menu-toggle');

    var $nav = $('#rv-mobile-nav');



    $toggle.on('click', function () {

        var isOpen = $nav.hasClass('open');

        $nav.toggleClass('open');

        $toggle.attr('aria-expanded', !isOpen);

        $nav.attr('aria-hidden', isOpen);

        $(this).find('i').toggleClass('fa-bars fa-times');

    });



    // Cerrar menú móvil al navegar (excepto cambio de sede)
    $nav.find('a').on('click', function () {
        if ($(this).hasClass('switch-subsidiary-item')) {
            return;
        }
        $nav.removeClass('open');
        $toggle.attr('aria-expanded', 'false');
        $nav.attr('aria-hidden', 'true');
        $toggle.find('i').removeClass('fa-times').addClass('fa-bars');
    });

    function getCsrfToken() {
        var match = document.cookie.match(/csrftoken=([^;]+)/);
        if (match) {
            return decodeURIComponent(match[1]);
        }
        var $input = $('input[name=csrfmiddlewaretoken]').first();
        return $input.length ? $input.val() : '';
    }

    function postSessionSwitch(url, data, onSuccess) {
        data.csrfmiddlewaretoken = getCsrfToken();
        $.post(url, data, function (response) {
            if (typeof toastr !== 'undefined') {
                toastr.success(response.message);
            }
            if (typeof onSuccess === 'function') {
                onSuccess(response);
            }
            setTimeout(function () {
                window.location.reload();
            }, 450);
        }).fail(function (jq) {
            var message = (jq.responseJSON && jq.responseJSON.message) || 'No se pudo completar el cambio';
            if (typeof toastr !== 'undefined') {
                toastr.error(message);
            }
        });
    }

    var $body = $('body');
    var switchSubsidiaryUrl = $body.data('switch-subsidiary-url');

    $(document).on('click', 'a.switch-subsidiary-item', function (e) {
        e.preventDefault();
        if ($(this).hasClass('active') || !switchSubsidiaryUrl) {
            return;
        }
        postSessionSwitch(switchSubsidiaryUrl, {
            subsidiary_id: $(this).data('subsidiary-id'),
        });
    });
})(jQuery);

