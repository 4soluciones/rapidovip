/**
 * Emisión de servicios — lógica centralizada (solo template principal carga este archivo).
 */
var GuideServices = (function ($) {
    'use strict';

    var cfg = {};
    var $form;
    var cashClosedWarned = false;

    var MSG_CASH_CLOSED = 'La caja se encuentra cerrada. Para registrar encomiendas, primero debe aperturar caja.';

    // Longitud exacta del número de documento según tipo (SUNAT: DNI 8, RUC 11)
    var DOC_LENGTHS = { '01': 8, '06': 11 };
    var DOC_NAMES = { '01': 'DNI', '06': 'RUC' };

    function docLengthFor(type) {
        return DOC_LENGTHS[type] || null;
    }

    function validateDocNumber(nro, type, who) {
        var len = docLengthFor(type);
        if (!len) return true;
        var value = String(nro || '').trim();
        if (!/^\d+$/.test(value) || value.length !== len) {
            toastr.warning('El ' + (DOC_NAMES[type] || 'documento') + (who ? ' del ' + who : '') +
                ' debe tener exactamente ' + len + ' dígitos');
            return false;
        }
        return true;
    }

    function applyDocMaxLength($input, type) {
        var len = docLengthFor(type);
        if (len) {
            $input.attr('maxlength', len);
            var v = String($input.val() || '');
            if (v.length > len) $input.val(v.slice(0, len));
        } else {
            $input.attr('maxlength', 20);
        }
    }

    function urls() {
        return {
            create: $form.data('url-create'),
            document: $form.data('url-document'),
            cashDate: $form.data('url-cash-date'),
            address: $form.data('url-address'),
            business: $form.data('url-business'),
            csrf: $form.data('csrf')
        };
    }

    function activeService() {
        return $('#id_service_type').val() || 'E';
    }

    function setService(svc) {
        $('#id_service_type').val(svc);
        if ($('.rv-guide-tab').length) {
            $('.rv-guide-tab').removeClass('active').attr('aria-selected', 'false');
            $('.rv-guide-tab[data-service="' + svc + '"]').addClass('active').attr('aria-selected', 'true');
        }
        if ($('.rv-guide-panel').length) {
            $('.rv-guide-panel').removeClass('is-active');
            $('#guide-panel-' + svc).addClass('is-active');
        }
        loadDocumentNumbers(svc);
    }

    function bindTabs() {
        if (!$('.rv-guide-tab').length) return;
        $('.rv-guide-tab').on('click', function () {
            setService($(this).data('service'));
        });
    }

    function setCashStatus(isOpen, label) {
        var $wrap = $('#guide-cash-status');
        $wrap.removeClass('is-open is-closed').addClass(isOpen ? 'is-open' : 'is-closed');
        $('#guide-cash-label').text(label);
    }

    function setSaveEnabled(enabled) {
        $('#id-btn-save, #e_btn_save_encomienda, #m_btn_save_mudanza, #d_btn_save_delivery, #c_btn_save_carga').prop('disabled', !enabled);
    }

    function saveButtonSelector(svc) {
        if (svc === 'M') return '#m_btn_save_mudanza';
        if (svc === 'D') return '#d_btn_save_delivery';
        if (svc === 'C') return '#c_btn_save_carga';
        return '#e_btn_save_encomienda';
    }

    function checkCashStatus() {
        var cashId = $('#id_cash').val();
        if (!cashId) {
            setCashStatus(false, 'Caja cerrada');
            setSaveEnabled(false);
            if (!cashClosedWarned) {
                cashClosedWarned = true;
                toastr.warning(MSG_CASH_CLOSED);
            }
            return;
        }
        setCashStatus(false, 'Verificando...');
        $.get(urls().cashDate, { cash_id: cashId }, function (r) {
            if (r.cash_id) $('#id_cash').val(r.cash_id);
            setCashStatus(true, 'Caja abierta');
            setSaveEnabled(true);
        }).fail(function () {
            setCashStatus(false, 'Caja cerrada');
            setSaveEnabled(false);
            if (!cashClosedWarned) {
                cashClosedWarned = true;
                toastr.warning(MSG_CASH_CLOSED);
            }
        });
    }

    function applyDocumentNumbers(serial, correlative) {
        $('#id_serie, #id_correlative')
            .val('')
            .prop('readonly', true)
            .addClass('rv-guide-doc-locked');
        $('#id_serie').val(serial || '');
        $('#id_correlative').val(correlative || '');
    }

    function applyOrderNumbers(serial, correlative) {
        $('#id_order_serie').val(serial || '');
        $('#id_order_correlative').val(correlative || '');
    }

    function toggleVoucherNumbers(docType) {
        var isVoucher = docType === 'B' || docType === 'F';
        $('.rv-guide-doc-voucher').toggle(isVoucher);
        $('#id_serie_label').text(docType === 'F' ? 'Factura' : 'Boleta');
        return isVoucher;
    }

    function loadDocumentNumbers(svc, docType) {
        docType = docType || (svc === 'E' ? ($('#e_type_bill').val() || 'T') : 'T');
        var u = urls();

        if (svc === 'E') {
            // Orden de servicio: todas las encomiendas usan la fila 'T'
            if (cfg.serviceDocs && cfg.serviceDocs.E && cfg.serviceDocs.E.T) {
                applyOrderNumbers(cfg.serviceDocs.E.T.serial, cfg.serviceDocs.E.T.correlative);
            }
            $.get(u.document, { service_type: 'E', document_type: 'T' }, function (r) {
                applyOrderNumbers(r.serial, r.correlative);
            });

            // Comprobante (boleta/factura): solo al contado
            if (!toggleVoucherNumbers(docType)) {
                applyDocumentNumbers('', '');
                return;
            }
            if (cfg.serviceDocs && cfg.serviceDocs.E && cfg.serviceDocs.E[docType]) {
                applyDocumentNumbers(
                    cfg.serviceDocs.E[docType].serial,
                    cfg.serviceDocs.E[docType].correlative
                );
            }
            $.get(u.document, { service_type: 'E', document_type: docType }, function (r) {
                applyDocumentNumbers(r.serial, r.correlative);
            });
            return;
        }

        if (cfg.serviceDocs && cfg.serviceDocs[svc]) {
            applyDocumentNumbers(
                cfg.serviceDocs[svc].serial,
                cfg.serviceDocs[svc].correlative
            );
        }

        $.get(u.document, { service_type: svc, document_type: docType }, function (r) {
            applyDocumentNumbers(r.serial, r.correlative);
        });
    }

    function bindEncomiendas() {
        $('#e_subsidiary_origin').on('change', function () {
            if ($(this).val() === '0') return;
            $.get(urls().address, { subsidiary_id: $(this).val() }, function (r) {
                $('#e_address_subsidiary').val(r.address_subsidiary);
            });
        });
        $('#e_subsidiary_destiny').on('change', function () {
            if ($(this).val() === '0') { $('#e_address_destiny').val(''); return; }
            $.get(urls().address, { subsidiary_id: $(this).val() }, function (r) {
                $('#e_address_destiny').val(r.address_subsidiary).css('background-color', r.color);
            });
        });
        $('#e_type_guide').on('change', function () {
            var ro = $(this).val() === 'O';
            $('#e_address_delivery').prop('readonly', ro);
            if (ro) $('#e_address_delivery').val('');
        });
        $('#e_transfer_date').on('change', function () {
            $('#id_transfer_date').val($(this).val() || '');
        });
        if ($('#e_transfer_date').val()) {
            $('#id_transfer_date').val($('#e_transfer_date').val());
        } else if ($('#e_issue_date').val()) {
            $('#e_transfer_date').val($('#e_issue_date').val());
            $('#id_transfer_date').val($('#e_issue_date').val());
        }
        if (!$('#e_issue_date').data('default-date')) {
            $('#e_issue_date').data('default-date', $('#e_issue_date').val());
        }
        if (!$('#e_transfer_date').data('default-date')) {
            $('#e_transfer_date').data('default-date', $('#e_transfer_date').val() || $('#e_issue_date').val());
        }

        function toggleSenderAddress() {
            var needAddress = $('#e_type_bill').val() === 'F' || $('#e_document_type_sender').val() === '06';
            if (needAddress) {
                $('.e-address-sender-wrap').show();
            } else {
                $('.e-address-sender-wrap').hide();
                $('#e_address_sender').val('');
            }
        }

        $('#e_type_bill').on('change', function () {
            var t = $(this).val();
            loadDocumentNumbers('E', t);
            if (t === 'F') {
                $('#e_document_type_sender').val('06');
                applyDocMaxLength($('#e_nro_document_sender'), '06');
            }
            toggleSenderAddress();
            recalcEncomiendaTotals();
        });

        function syncDocTypeByPayment() {
            var pay = $('#e_way_to_pay').val();
            var $bill = $('#e_type_bill');
            if (!$bill.length) return;
            var current = $bill.val();
            $bill.find('option').prop('disabled', false).show();
            if (pay === 'C') {
                // Al contado: solo boleta o factura
                $bill.find('option[value="T"]').prop('disabled', true).hide();
                if (current === 'T' || !current) {
                    $bill.val('B');
                }
            } else if (pay === 'D') {
                // Pago destino: solo ticket
                $bill.find('option[value="B"], option[value="F"]').prop('disabled', true).hide();
                $bill.val('T');
            }
            $bill.trigger('change');
        }

        $('#e_way_to_pay').on('change', syncDocTypeByPayment);
        syncDocTypeByPayment();

        $('#e_document_type_sender').on('change', function () {
            toggleSenderAddress();
            applyDocMaxLength($('#e_nro_document_sender'), $(this).val());
        });
        applyDocMaxLength($('#e_nro_document_sender'), $('#e_document_type_sender').val());
        $(document).on('change', '.e-document-type-addressee', function () {
            var $row = $(this).closest('.e-addressee-row');
            applyDocMaxLength($row.find('.e-nro-document-addressee'), $(this).val());
        });
        $(document).on('input', '#e_nro_document_sender, .e-nro-document-addressee', function () {
            var type = $(this).is('#e_nro_document_sender')
                ? $('#e_document_type_sender').val()
                : $(this).closest('.e-addressee-row').find('.e-document-type-addressee').val();
            if (docLengthFor(type)) {
                var clean = String($(this).val() || '').replace(/\D/g, '');
                if (clean !== $(this).val()) $(this).val(clean);
            }
        });
        $('#e_detail_price').on('input', function () {
            var q = parseFloat($('#e_detail_qty').val()) || 0;
            var p = parseFloat($(this).val()) || 0;
            $('#e_detail_amount').val((q * p).toFixed(2));
        });
        $('#e_detail_amount').on('input', function () {
            var q = parseFloat($('#e_detail_qty').val()) || 1;
            var a = parseFloat($(this).val()) || 0;
            $('#e_detail_price').val((a / q).toFixed(6));
        });
        $('#e_add_detail').on('click', addEncomiendaDetail);
        $(document).on('click', '.e-remove-detail', function () {
            $(this).closest('.rv-guide-e-detail-row').remove();
            recalcEncomiendaTotals();
        });
        function searchSender() {
            if (!validateDocNumber($('#e_nro_document_sender').val(), $('#e_document_type_sender').val(), 'remitente')) return;
            searchBusiness(
                $('#e_nro_document_sender').val(),
                $('#e_document_type_sender').val(),
                function (r) {
                    $('#e_sender').val(r.result);
                    $('#e_address_sender').val(r.address || '');
                    $('#e_phone_sender').val(r.phone || '');
                },
                { $group: $('#e_sender_doc_group') }
            );
        }

        function searchAddressee($row) {
            if (!validateDocNumber($row.find('.e-nro-document-addressee').val(), $row.find('.e-document-type-addressee').val(), 'destinatario')) return;
            searchBusiness(
                $row.find('.e-nro-document-addressee').val(),
                $row.find('.e-document-type-addressee').val(),
                function (r) {
                    $row.find('.e-name-addressee').val(r.result);
                    $row.find('.e-phone-addressee').val(r.phone || '');
                },
                { $group: $row.find('.e-addressee-doc-group') }
            );
        }

        $('#e_btn_search_sender').on('click', searchSender);
        $(document).on('click', '.e-btn-search-addressee', function () {
            searchAddressee($(this).closest('.e-addressee-row'));
        });

        function triggerDocumentSearch($input) {
            if ($input.is('#e_nro_document_sender')) {
                searchSender();
                return;
            }
            if ($input.is('.e-nro-document-addressee')) {
                searchAddressee($input.closest('.e-addressee-row'));
            }
        }

        $form.on('keydown', '#e_nro_document_sender, .e-nro-document-addressee', function (e) {
            if (e.key === 'Enter' || e.which === 13) {
                e.preventDefault();
                e.stopPropagation();
                triggerDocumentSearch($(this));
                return false;
            }
        });

        $form.on('submit', function (e) {
            var $active = $(document.activeElement);
            if ($active.is('#e_nro_document_sender, .e-nro-document-addressee')) {
                e.preventDefault();
                e.stopImmediatePropagation();
                triggerDocumentSearch($active);
                return false;
            }
        });
        $('#e_add_addressee').on('click', function () {
            var $clone = $('.e-addressee-row').first().clone();
            $clone.find('input').val('');
            $clone.find('.rv-form-group-action').html(
                '<label>&nbsp;</label><button type="button" class="rv-btn rv-btn-outline rv-btn-sm e-remove-addressee"><i class="fas fa-minus"></i></button>'
            );
            $('.e-addressee-rows').append($clone);
            applyDocMaxLength($clone.find('.e-nro-document-addressee'), $clone.find('.e-document-type-addressee').val());
        });
        $(document).on('click', '.e-remove-addressee', function () {
            if ($('.e-addressee-row').length > 1) $(this).closest('.e-addressee-row').remove();
        });
        $('#e_btn_clear').on('click', clearEncomiendaForm);
        $('#e_btn_cancel').on('click', function () { location.reload(); });
    }

    function clearEncomiendaForm() {
        $('#e_way_to_pay').val($('#e_way_to_pay option:first').val()).trigger('change');
        $('#e_code').val('');
        var defaultIssueDate = $('#e_issue_date').data('default-date') || $('#e_issue_date').attr('value') || '';
        var defaultTransferDate = $('#e_transfer_date').data('default-date') || defaultIssueDate;
        $('#e_issue_date').val(defaultIssueDate);
        $('#e_transfer_date').val(defaultTransferDate);
        $('#id_transfer_date').val(defaultTransferDate);
        var originDefault = $('#e_subsidiary_origin').data('default');
        if (originDefault) {
            $('#e_subsidiary_origin').val(String(originDefault));
        }
        $('#e_subsidiary_destiny').val('0');
        $('#e_address_subsidiary, #e_address_destiny, #e_address_delivery, #e_address_sender').val('');
        $('#e_address_destiny').css('background-color', '');
        $('#e_type_guide').val($('#e_type_guide option:first').val()).trigger('change');
        $('#e_document_type_sender').val('01');
        $('#e_nro_document_sender, #e_sender, #e_phone_sender').val('');
        applyDocMaxLength($('#e_nro_document_sender'), '01');
        $('.e-address-sender-wrap').hide();
        $('.e-addressee-row').not(':first').remove();
        $('.e-addressee-row:first').find('input').val('');
        $('.e-addressee-row:first').find('select').prop('selectedIndex', 0);
        applyDocMaxLength($('.e-addressee-row:first').find('.e-nro-document-addressee'), '01');
        $('#e_details_body').empty();
        $('#e_detail_desc, #e_detail_price, #e_detail_amount, #e_detail_weight').val('');
        $('#e_detail_qty').val('1');
        $('#e_observation').val('');
        recalcEncomiendaTotals();
        $('#e_subsidiary_origin').trigger('change');
    }

    function clearMudanzaForm() {
        $('#m_origin_address, #m_dest_address, #m_item_desc, #m_fare_amount').val('');
        $('#m_origin_property_type, #m_dest_property_type').val('C');
        $('#m_origin_floors, #m_dest_floors').val('1');
        $('#m_helpers_count').val('0');
        $('#m_payment_method').val('E');
        $('#m_item_qty').val('1');
        $('#m_service_date').val($('#m_service_date').data('default-date') || $('#m_service_date').attr('value') || '');
        $('#m_service_time').val($('#m_service_time').data('default-time') || $('#m_service_time').attr('value') || '');
        $('#m_inventory_body').empty();
        $('#m_fare_display').text('0.00');
        updateServiceDetailState($('#m_inventory_body'), $('#m_inventory_empty'), $('#m_detail_count'));
    }

    function clearDeliveryForm() {
        $('#d_origin_address, #d_dest_client, #d_dest_phone, #d_dest_address, #d_dest_reference').val('');
        $('#d_item_desc, #d_item_price, #d_fare_amount').val('');
        $('#d_payment_method').val('E');
        $('#d_shipment_body').empty();
        $('.d-shipment-total, #d_fare_display').text('0.00');
        updateServiceDetailState($('#d_shipment_body'), $('#d_shipment_empty'), $('#d_detail_count'));
    }

    function clearCargaForm() {
        $('#c_client_ruc, #c_client_name, #c_origin_address, #c_origin_contact, #c_origin_phone').val('');
        $('#c_dest_address, #c_dest_contact, #c_dest_phone, #c_cargo_type, #c_cargo_price, #c_fare_amount').val('');
        $('#c_cargo_qty').val('1');
        $('#c_payment_method').val('E');
        $('#c_cargo_body').empty();
        $('.c-cargo-total, #c_fare_display').text('0.00');
        updateServiceDetailState($('#c_cargo_body'), $('#c_cargo_empty'), $('#c_detail_count'));
    }

    function resetFormAfterSave() {
        var svc = activeService();
        if (svc === 'E') {
            clearEncomiendaForm();
        } else if (svc === 'M') {
            clearMudanzaForm();
        } else if (svc === 'D') {
            clearDeliveryForm();
        } else if (svc === 'C') {
            clearCargaForm();
        }
        loadDocumentNumbers(svc, svc === 'E' ? $('#e_type_bill').val() : 'T');
    }

    function downloadPdf(url, filename) {
        if (!url) return;
        var isExternal = /^https?:\/\//i.test(url) && url.indexOf(window.location.origin) !== 0;

        function saveBlob(blob) {
            var blobUrl = window.URL.createObjectURL(blob);
            var link = document.createElement('a');
            link.href = blobUrl;
            link.download = filename;
            link.style.display = 'none';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(blobUrl);
        }

        if (isExternal) {
            fetch(url, { mode: 'cors' })
                .then(function (res) {
                    if (!res.ok) throw new Error('download failed');
                    return res.blob();
                })
                .then(saveBlob)
                .catch(function () {
                    var link = document.createElement('a');
                    link.href = url;
                    link.download = filename;
                    link.style.display = 'none';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                });
            return;
        }

        fetch(url, { credentials: 'same-origin' })
            .then(function (res) {
                if (!res.ok) throw new Error('download failed');
                return res.blob();
            })
            .then(saveBlob)
            .catch(function () {
                toastr.warning('No se pudo descargar el documento');
            });
    }

    function downloadComprobante(response) {
        if (!response || !response.order_id) return;
        var url;
        var filename = 'comprobante-' + response.order_id + '.pdf';
        if (response.sunat_pdf) {
            url = response.sunat_pdf;
            filename = 'comprobante-sunat-' + response.order_id + '.pdf';
        } else if (response.document_type === 'B' || response.document_type === 'F') {
            url = '/comercial/print_bill_order_commodity/' + response.order_id + '/?download=1';
        } else {
            url = '/comercial/print_ticket_order_commodity/' + response.order_id + '/?download=1';
            filename = 'ORDEN DE SERVICIO ' + (response.serial || '') + '-' + (response.correlative || '') + '.pdf';
        }
        downloadPdf(url, filename);
    }

    function downloadOrdenServicio(response) {
        if (!response || !response.order_id) return;
        var serial = response.order_serial || response.serial || '';
        var correlative = response.order_correlative || response.correlative || '';
        var filename = 'ORDEN DE SERVICIO ' + serial + '-' + correlative + '.pdf';
        var url = '/comercial/print_ticket_order_commodity/' + response.order_id + '/?download=1';
        downloadPdf(url, filename);
    }

    function downloadVoucher(response) {
        if (!response || !response.order_id) return;
        var url;
        var filename = 'comprobante-' + response.order_id + '.pdf';
        if (response.sunat_pdf) {
            url = response.sunat_pdf;
            filename = 'comprobante-sunat-' + response.order_id + '.pdf';
        } else {
            url = '/comercial/print_bill_order_commodity/' + response.order_id + '/?download=1';
            var docLabel = response.document_type === 'F' ? 'FACTURA' : 'BOLETA';
            filename = docLabel + ' ' + (response.serial || '') + '-' + (response.correlative || '') + '.pdf';
        }
        downloadPdf(url, filename);
    }

    function formatMoney(value) {
        var n = parseFloat(value);
        if (isNaN(n)) n = 0;
        return 'S/ ' + n.toFixed(2);
    }

    function formatOsNumber(response) {
        var serial = (response.order_serial || '').toString().trim();
        var correlative = (response.order_correlative || '').toString().trim();
        if (serial && correlative) return serial + '-' + correlative;
        if (response.serial && response.correlative) return response.serial + '-' + response.correlative;
        return response.order_id ? ('OS-' + response.order_id) : '—';
    }

    function paymentLabel(code) {
        if (code === 'D') return 'Pago destino';
        if (code === 'C') return 'Al contado';
        if (code === 'S') return 'Servicio';
        return 'Otro';
    }

    function voucherTitle(docType) {
        if (docType === 'F') return 'Factura';
        if (docType === 'B') return 'Boleta';
        return 'Comprobante';
    }

    var pendingPrintResponse = null;

    function openPrintModal(response, context) {
        pendingPrintResponse = response || null;
        if (!pendingPrintResponse || !pendingPrintResponse.order_id) return;

        var wayToPay = response.way_to_pay || (context && context.wayToPay) || 'C';
        var docType = response.document_type;
        if (docType !== 'B' && docType !== 'F') {
            docType = (context && context.docType) || docType;
        }
        var showVoucher = wayToPay === 'C' && (docType === 'B' || docType === 'F');
        var osNumber = formatOsNumber(response);
        var voucherNumber = (response.serial || '') + '-' + (response.correlative || '');
        var total = formatMoney(response.total != null ? response.total : (context && context.total));
        var routeText = (context && context.routeText) || '';

        $('#guide-print-os-number').text(osNumber);
        $('#guide-print-payment').text(paymentLabel(wayToPay));
        $('#guide-print-total').text(total);
        $('#guide-print-os-label').text('N° ' + osNumber);

        if (routeText) {
            $('#guide-print-route-text').text(routeText);
            $('#guide-print-route').prop('hidden', false);
        } else {
            $('#guide-print-route').prop('hidden', true);
        }

        if (showVoucher) {
            $('#guide-print-voucher-title').text(voucherTitle(docType));
            $('#guide-print-voucher-label').text('N° ' + voucherNumber);
            $('#guide-print-btn-voucher').prop('hidden', false);
            $('#guide-print-actions').removeClass('is-single').addClass('is-dual');
            $('#guide-print-subtitle').text('Descargue la orden de servicio y el comprobante');
        } else {
            $('#guide-print-btn-voucher').prop('hidden', true);
            $('#guide-print-actions').removeClass('is-dual').addClass('is-single');
            $('#guide-print-subtitle').text('Descargue la orden de servicio');
        }

        $('#guide-print-btn-os, #guide-print-btn-voucher').prop('disabled', false);
        $('#guide-print-modal').modal('show');
    }

    function capturePrintContext() {
        var origin = ($('#e_subsidiary_origin option:selected').text() || '').trim();
        var destiny = ($('#e_subsidiary_destiny option:selected').text() || '').trim();
        var routeText = '';
        if (origin && destiny && destiny.toLowerCase().indexOf('seleccione') === -1) {
            routeText = origin + ' → ' + destiny;
        }
        return {
            wayToPay: $('#e_way_to_pay').val() || 'C',
            docType: $('#e_type_bill').val() || 'T',
            total: $('.e-total').first().text() || '0.00',
            routeText: routeText
        };
    }

    function bindPrintModal() {
        $('#guide-print-btn-os').on('click', function () {
            if (!pendingPrintResponse) return;
            var $btn = $(this).prop('disabled', true);
            downloadOrdenServicio(pendingPrintResponse);
            setTimeout(function () { $btn.prop('disabled', false); }, 1200);
        });
        $('#guide-print-btn-voucher').on('click', function () {
            if (!pendingPrintResponse) return;
            var $btn = $(this).prop('disabled', true);
            downloadVoucher(pendingPrintResponse);
            setTimeout(function () { $btn.prop('disabled', false); }, 1200);
        });
        $('#guide-print-modal').on('hidden.bs.modal', function () {
            pendingPrintResponse = null;
        });
    }

    function handleSaveSuccess(response) {
        toastr.success(response.message);
        var svc = activeService();
        if (svc === 'E' && response && response.order_id) {
            var context = capturePrintContext();
            openPrintModal(response, context);
            resetFormAfterSave();
            return;
        }
        downloadComprobante(response);
        resetFormAfterSave();
    }

    function setDocSearchLoading(ui, loading) {
        if (!ui) return;
        var $group = ui.$group;
        if (!$group || !$group.length) return;
        $group.toggleClass('is-searching', loading);
        $group.find('.rv-doc-search-overlay').attr('aria-busy', loading ? 'true' : 'false');
        $group.find('.rv-doc-search-btn').prop('disabled', loading);
    }

    function searchBusiness(nro, type, cb, ui) {
        if (!nro || !String(nro).trim()) {
            toastr.warning('Ingrese número de documento');
            return;
        }
        setDocSearchLoading(ui, true);
        $.get(urls().business, { nro_document: nro, type: type }, function (r) {
            cb(r);
        }).fail(function (xhr) {
            toastr.error(xhr.responseJSON?.error || 'No encontrado');
        }).always(function () {
            setDocSearchLoading(ui, false);
        });
    }

    function addEncomiendaDetail() {
        var qty = parseFloat($('#e_detail_qty').val()) || 0;
        var desc = ($('#e_detail_desc').val() || '').trim();
        var weightRaw = ($('#e_detail_weight').val() || '').trim();
        var weight = weightRaw === '' ? null : parseFloat(weightRaw);
        var price = parseFloat($('#e_detail_price').val()) || 0;
        var amount = parseFloat($('#e_detail_amount').val()) || 0;
        if (!desc) { toastr.warning('Ingrese descripción'); return; }
        if (qty <= 0) { toastr.warning('Cantidad inválida'); return; }
        if (!$('#e_detail_unit').val()) {
            toastr.warning('Escoja una unidad');
            $('#e_detail_unit').focus();
            return;
        }
        if (weight === null || isNaN(weight) || weight <= 0) {
            toastr.warning('Ingrese el peso del ítem');
            $('#e_detail_weight').focus();
            return;
        }
        var weightDisplay = weight.toFixed(2) + ' kg';
        var weightValue = weight.toFixed(2);
        var unitId = $('#e_detail_unit').val() || '';
        var unitLabel = ($('#e_detail_unit option:selected').text() || 'SIN UND').trim().toUpperCase();
        $('#e_details_body').append(
            '<div class="rv-guide-e-detail-row">' +
                '<span class="e-item-qty">' + qty + '</span>' +
                '<span class="e-item-unit text-center" data-unit-id="' + unitId + '">' + unitLabel + '</span>' +
                '<span class="e-item-desc">' + desc.toUpperCase() + '</span>' +
                '<span class="e-item-weight text-right" data-weight="' + weightValue + '">' + weightDisplay + '</span>' +
                '<span class="e-item-price text-right item-price">' + price.toFixed(2) + '</span>' +
                '<span class="e-item-amount text-right item-amount">' + amount.toFixed(2) + '</span>' +
                '<button type="button" class="rv-btn rv-btn-outline rv-btn-sm e-remove-detail" title="Quitar">' +
                    '<i class="fas fa-trash-alt"></i>' +
                '</button>' +
            '</div>'
        );
        $('#e_detail_desc, #e_detail_price, #e_detail_amount, #e_detail_weight').val('');
        $('#e_detail_qty').val('1');
        $('#e_detail_desc').focus();
        recalcEncomiendaTotals();
    }

    function recalcEncomiendaTotals() {
        var sum = 0;
        var count = $('#e_details_body .rv-guide-e-detail-row').length;
        $('#e_details_body .item-amount').each(function () {
            sum += parseFloat($(this).text()) || 0;
        });
        var isFactura = $('#e_type_bill').val() === 'F';
        if (isFactura) {
            var sub = sum / 1.18;
            $('.e-subtotal').text(sub.toFixed(2));
            $('.e-igv').text((sum - sub).toFixed(2));
        } else {
            $('.e-subtotal, .e-igv').text('0.00');
        }
        $('.e-total').text(sum.toFixed(2));
        $('#e_detail_count').text(count === 1 ? '1 ítem' : count + ' ítems');
        $('#e_details_empty').toggle(count === 0);
    }

    function updateServiceDetailState($list, $empty, $countEl) {
        var count = $list.children('.rv-guide-e-detail-row').length;
        if ($countEl && $countEl.length) {
            $countEl.text(count === 1 ? '1 ítem' : count + ' ítems');
        }
        if ($empty && $empty.length) {
            $empty.toggle(count === 0);
        }
        return count;
    }

    function bindMudanza() {
        $('#m_service_date').on('change', function () {
            $('#id_transfer_date').val($(this).val() || '');
        });
        $('#m_fare_amount').on('input', function () {
            $('#m_fare_display').text((parseFloat($(this).val()) || 0).toFixed(2));
        });
        $('#m_add_item').on('click', function () {
            var d = ($('#m_item_desc').val() || '').trim();
            var q = parseInt($('#m_item_qty').val(), 10) || 0;
            if (!d) { toastr.warning('Ingrese artículo'); return; }
            if (q <= 0) { toastr.warning('Cantidad inválida'); return; }
            $('#m_inventory_body').append(
                '<div class="rv-guide-e-detail-row rv-guide-e-detail-row--2">' +
                    '<span class="e-item-qty item-qty">' + q + '</span>' +
                    '<span class="e-item-desc item-desc">' + d.toUpperCase() + '</span>' +
                    '<button type="button" class="rv-btn rv-btn-outline rv-btn-sm m-remove-row e-remove-detail" title="Quitar">' +
                        '<i class="fas fa-trash-alt"></i>' +
                    '</button>' +
                '</div>'
            );
            $('#m_item_desc').val('');
            $('#m_item_qty').val('1');
            updateServiceDetailState($('#m_inventory_body'), $('#m_inventory_empty'), $('#m_detail_count'));
        });
        $('#m_btn_clear').on('click', clearMudanzaForm);
    }

    function bindDelivery() {
        $('#d_add_item').on('click', function () {
            var d = ($('#d_item_desc').val() || '').trim();
            var p = parseFloat($('#d_item_price').val()) || 0;
            if (!d) { toastr.warning('Ingrese descripción'); return; }
            $('#d_shipment_body').append(
                '<div class="rv-guide-e-detail-row rv-guide-e-detail-row--3">' +
                    '<span class="e-item-desc item-desc">' + d.toUpperCase() + '</span>' +
                    '<span class="e-item-amount item-price text-right">' + p.toFixed(2) + '</span>' +
                    '<button type="button" class="rv-btn rv-btn-outline rv-btn-sm d-remove-row e-remove-detail" title="Quitar">' +
                        '<i class="fas fa-trash-alt"></i>' +
                    '</button>' +
                '</div>'
            );
            $('#d_item_desc, #d_item_price').val('');
            recalcDeliveryTotal();
        });
        $('#d_fare_amount').on('input', recalcDeliveryTotal);
        $('#d_btn_clear').on('click', clearDeliveryForm);
    }

    function recalcDeliveryTotal() {
        var sum = 0;
        $('#d_shipment_body .item-price').each(function () { sum += parseFloat($(this).text()) || 0; });
        if (!$('#d_fare_amount').val()) $('#d_fare_amount').val(sum.toFixed(2));
        $('.d-shipment-total').text(sum.toFixed(2));
        var fare = parseFloat($('#d_fare_amount').val()) || sum;
        $('#d_fare_display').text(fare.toFixed(2));
        updateServiceDetailState($('#d_shipment_body'), $('#d_shipment_empty'), $('#d_detail_count'));
    }

    function bindCarga() {
        $('#c_btn_search_ruc').on('click', function () {
            searchBusiness($('#c_client_ruc').val(), '06', function (r) {
                $('#c_client_name').val(r.result);
            }, { $group: $('#c_ruc_doc_group') });
        });
        $('#c_add_cargo').on('click', function () {
            var t = ($('#c_cargo_type').val() || '').trim();
            var q = parseInt($('#c_cargo_qty').val(), 10) || 0;
            var p = parseFloat($('#c_cargo_price').val()) || 0;
            if (!t) { toastr.warning('Ingrese tipo de carga'); return; }
            if (q <= 0) { toastr.warning('Cantidad inválida'); return; }
            $('#c_cargo_body').append(
                '<div class="rv-guide-e-detail-row rv-guide-e-detail-row--cargo">' +
                    '<span class="e-item-qty item-qty">' + q + '</span>' +
                    '<span class="e-item-desc item-desc">' + t.toUpperCase() + '</span>' +
                    '<span class="e-item-amount item-price text-right">' + p.toFixed(2) + '</span>' +
                    '<button type="button" class="rv-btn rv-btn-outline rv-btn-sm c-remove-row e-remove-detail" title="Quitar">' +
                        '<i class="fas fa-trash-alt"></i>' +
                    '</button>' +
                '</div>'
            );
            $('#c_cargo_type, #c_cargo_price').val('');
            $('#c_cargo_qty').val('1');
            recalcCargaTotal();
        });
        $('#c_fare_amount').on('input', recalcCargaTotal);
        $('#c_btn_clear').on('click', clearCargaForm);
    }

    $(document).on('click', '.m-remove-row, .d-remove-row, .c-remove-row', function () {
        $(this).closest('.rv-guide-e-detail-row').remove();
        recalcDeliveryTotal();
        recalcCargaTotal();
        updateServiceDetailState($('#m_inventory_body'), $('#m_inventory_empty'), $('#m_detail_count'));
    });

    function recalcCargaTotal() {
        var sum = 0;
        $('#c_cargo_body .item-price').each(function () { sum += parseFloat($(this).text()) || 0; });
        if (!$('#c_fare_amount').val()) $('#c_fare_amount').val(sum.toFixed(2));
        $('.c-cargo-total').text(sum.toFixed(2));
        var fare = parseFloat($('#c_fare_amount').val()) || sum;
        $('#c_fare_display').text(fare.toFixed(2));
        updateServiceDetailState($('#c_cargo_body'), $('#c_cargo_empty'), $('#c_detail_count'));
    }

    function validate() {
        var svc = activeService();
        var $btn = $(saveButtonSelector(svc));
        if ($btn.length && $btn.prop('disabled')) { toastr.warning(MSG_CASH_CLOSED); return false; }

        if (svc === 'E') {
            if (!$('#e_transfer_date').val()) {
                toastr.warning('Ingrese la fecha de traslado'); return false;
            }
            if ($('#e_subsidiary_origin').val() === '0' || $('#e_subsidiary_destiny').val() === '0') {
                toastr.warning('Seleccione origen y destino'); return false;
            }
            if ($('#e_details_body .rv-guide-e-detail-row').length === 0) { toastr.warning('Agregue detalle de encomienda'); return false; }
            if ($('#e_nro_document_sender').val() &&
                !validateDocNumber($('#e_nro_document_sender').val(), $('#e_document_type_sender').val(), 'remitente')) {
                return false;
            }
            var addresseeDocsOk = true;
            $('.e-addressee-row').each(function () {
                var nro = $(this).find('.e-nro-document-addressee').val();
                if (nro && !validateDocNumber(nro, $(this).find('.e-document-type-addressee').val(), 'destinatario')) {
                    addresseeDocsOk = false;
                    return false;
                }
            });
            if (!addresseeDocsOk) return false;
            var phoneOk = false;
            $('.e-phone-addressee').each(function () { if ($(this).val()) phoneOk = true; });
            if (!phoneOk) { toastr.warning('Ingrese teléfono del destinatario'); return false; }
        }
        if (svc === 'M') {
            if (!$('#m_origin_address').val() || !$('#m_dest_address').val()) { toastr.warning('Complete direcciones'); return false; }
            if ($('#m_inventory_body .rv-guide-e-detail-row').length === 0) { toastr.warning('Agregue inventario'); return false; }
            if (!$('#m_fare_amount').val()) { toastr.warning('Ingrese tarifa'); return false; }
        }
        if (svc === 'D') {
            if (!$('#d_origin_address').val() || !$('#d_dest_address').val() || !$('#d_dest_client').val()) {
                toastr.warning('Complete origen y destino'); return false;
            }
            if ($('#d_shipment_body .rv-guide-e-detail-row').length === 0) { toastr.warning('Agregue detalle del envío'); return false; }
            if (!$('#d_fare_amount').val()) { toastr.warning('Ingrese tarifa'); return false; }
        }
        if (svc === 'C') {
            if (!$('#c_client_ruc').val() || !$('#c_client_name').val()) { toastr.warning('Complete cliente'); return false; }
            if (!$('#c_origin_address').val() || !$('#c_dest_address').val()) { toastr.warning('Complete origen y destino'); return false; }
            if ($('#c_cargo_body .rv-guide-e-detail-row').length === 0) { toastr.warning('Agregue mercancía'); return false; }
        }
        return true;
    }

    function collectPayload() {
        var svc = activeService();
        var payload = {
            Service_Type: svc,
            Serial: $('#id_serie').val(),
            Correlative: $('#id_correlative').val(),
            Order_Serial: $('#id_order_serie').val(),
            Order_Correlative: $('#id_order_correlative').val(),
            User: $('#id_user').val(),
            Date_transfer: $('#id_transfer_date').val() || $('#e_transfer_date').val(),
            Cash: $('#id_cash').val(),
            Demo: 0,
            Employee: 0,
            Plate: '',
            Details: [],
            Addressees: [],
            Service_Extra: {}
        };

        if (svc === 'E') {
            payload.Subsidiary_origin = $('#e_subsidiary_origin').val();
            payload.Subsidiary_destiny = $('#e_subsidiary_destiny').val();
            payload.Type = $('#e_type_bill').val();
            payload.Way_to_pay = $('#e_way_to_pay').val();
            payload.Type_Guide = $('#e_type_guide').val();
            payload.Address_Delivery = $('#e_address_delivery').val();
            payload.Arrival_Time = '';
            payload.Code = ($('#e_code').val() || '').trim() || '0000';
            payload.Client_Sender_nro_document = $('#e_nro_document_sender').val();
            payload.Client_Sender = $('#e_sender').val();
            payload.Client_Address_Sender = $('#e_address_sender').val();
            payload.Client_Sender_type = $('#e_document_type_sender').val();
            payload.Client_Sender_phone = $('#e_phone_sender').val();
            payload.Client_Address_Sender = $('#e_address_sender').val();
            payload.Igv = $('.e-igv').text();
            payload.Sub_total = $('.e-subtotal').text();
            payload.Total = $('.e-total').text();
            payload.Observation = ($('#e_observation').val() || '').trim();
            $('#e_details_body .rv-guide-e-detail-row').each(function () {
                payload.Details.push({
                    Quantity: $(this).find('.e-item-qty').text(),
                    Description: $(this).find('.e-item-desc').text(),
                    Weight: $(this).find('.e-item-weight').attr('data-weight') || '',
                    Price_unit: $(this).find('.item-price').text(),
                    Amount: $(this).find('.item-amount').text(),
                    Unit: $(this).find('.e-item-unit').attr('data-unit-id') || $('#e_detail_unit').val() || ''
                });
            });
            $('.e-addressee-row').each(function () {
                payload.Addressees.push({
                    DocumentType: $(this).find('.e-document-type-addressee').val(),
                    DocumentNumber: $(this).find('.e-nro-document-addressee').val(),
                    Name: $(this).find('.e-name-addressee').val(),
                    Phone: $(this).find('.e-phone-addressee').val()
                });
            });
        } else {
            payload.Type = 'T';
            payload.Way_to_pay = 'C';
            payload.Type_Guide = 'O';
            payload.Arrival_Time = '00:00';
            payload.Code = '0000';
            payload.Client_Sender = '';
            payload.Client_Sender_nro_document = '';
            payload.Client_Address_Sender = '';
            payload.Client_Sender_type = '01';
            payload.Client_Sender_phone = '';
            payload.Address_Delivery = '';
            payload.Subsidiary_origin = '0';
            payload.Subsidiary_destiny = '0';

            if (svc === 'M') {
                payload.Total = $('#m_fare_amount').val();
                payload.Sub_total = payload.Total;
                payload.Igv = '0';
                payload.Service_Extra = {
                    origin_address: $('#m_origin_address').val(),
                    origin_property_type: $('#m_origin_property_type').val(),
                    origin_floors: $('#m_origin_floors').val(),
                    dest_address: $('#m_dest_address').val(),
                    dest_property_type: $('#m_dest_property_type').val(),
                    dest_floors: $('#m_dest_floors').val(),
                    service_date: $('#m_service_date').val(),
                    service_time: $('#m_service_time').val(),
                    helpers_count: $('#m_helpers_count').val(),
                    fare_amount: $('#m_fare_amount').val(),
                    payment_method: $('#m_payment_method').val()
                };
                $('#m_inventory_body .rv-guide-e-detail-row').each(function () {
                    payload.Details.push({
                        Quantity: $(this).find('.item-qty').text(),
                        Description: $(this).find('.item-desc').text(),
                        Price_unit: 0,
                        Amount: 0,
                        Unit: 1
                    });
                });
                payload.Addressees.push({ DocumentType: '01', DocumentNumber: '', Name: 'MUDANZA', Phone: '000000000' });
            }
            if (svc === 'D') {
                payload.Total = $('#d_fare_amount').val();
                payload.Sub_total = payload.Total;
                payload.Igv = '0';
                payload.Service_Extra = {
                    origin_address: $('#d_origin_address').val(),
                    dest_address: $('#d_dest_address').val(),
                    dest_contact: $('#d_dest_client').val(),
                    dest_phone: $('#d_dest_phone').val(),
                    dest_reference: $('#d_dest_reference').val(),
                    fare_amount: $('#d_fare_amount').val(),
                    payment_method: $('#d_payment_method').val()
                };
                $('#d_shipment_body .rv-guide-e-detail-row').each(function () {
                    var p = parseFloat($(this).find('.item-price').text()) || 0;
                    payload.Details.push({
                        Quantity: 1,
                        Description: $(this).find('.item-desc').text(),
                        Price_unit: p,
                        Amount: p,
                        Unit: 1
                    });
                });
                payload.Addressees.push({
                    DocumentType: '01', DocumentNumber: '', Name: $('#d_dest_client').val(), Phone: $('#d_dest_phone').val()
                });
            }
            if (svc === 'C') {
                payload.Total = $('#c_fare_amount').val();
                payload.Sub_total = payload.Total;
                payload.Igv = '0';
                payload.Service_Extra = {
                    client_ruc: $('#c_client_ruc').val(),
                    client_name: $('#c_client_name').val(),
                    origin_address: $('#c_origin_address').val(),
                    origin_contact: $('#c_origin_contact').val(),
                    origin_phone: $('#c_origin_phone').val(),
                    dest_address: $('#c_dest_address').val(),
                    dest_contact: $('#c_dest_contact').val(),
                    dest_phone: $('#c_dest_phone').val(),
                    fare_amount: $('#c_fare_amount').val(),
                    payment_method: $('#c_payment_method').val()
                };
                $('#c_cargo_body .rv-guide-e-detail-row').each(function () {
                    var p = parseFloat($(this).find('.item-price').text()) || 0;
                    var q = parseInt($(this).find('.item-qty').text(), 10) || 1;
                    payload.Details.push({
                        Quantity: q,
                        Description: $(this).find('.item-desc').text(),
                        Price_unit: p,
                        Amount: (p * q).toFixed(2),
                        Unit: 1
                    });
                });
                payload.Client_Sender_nro_document = $('#c_client_ruc').val();
                payload.Client_Sender = $('#c_client_name').val();
                payload.Client_Sender_type = '06';
                payload.Addressees.push({ DocumentType: '06', DocumentNumber: $('#c_client_ruc').val(), Name: $('#c_client_name').val(), Phone: '' });
            }
        }
        return payload;
    }

    function bindSubmit() {
        $form.on('submit', function (e) {
            e.preventDefault();
            if (!validate()) return;
            var orders = collectPayload();
            $('#guide-loading').show();
            $('#id-btn-save, #e_btn_save_encomienda, #m_btn_save_mudanza, #d_btn_save_delivery, #c_btn_save_carga').prop('disabled', true);
            $.ajax({
                url: urls().create,
                type: 'GET',
                data: { orders: JSON.stringify(orders) },
                success: function (response) {
                    handleSaveSuccess(response);
                },
                error: function (xhr) {
                    toastr.error(xhr.responseJSON?.error || 'Error al guardar');
                },
                complete: function () {
                    $('#guide-loading').hide();
                    checkCashStatus();
                }
            });
        });
    }

    function init(options) {
        cfg = options || {};
        $form = $('#new-guide-form');
        bindTabs();
        bindEncomiendas();
        bindMudanza();
        bindDelivery();
        bindCarga();
        bindPrintModal();
        $('.rv-guide-btn-cancel').on('click', function () { location.reload(); });
        bindSubmit();
        setService(cfg.defaultService || activeService() || 'E');
        if ($('#m_service_date').length && !$('#m_service_date').data('default-date')) {
            $('#m_service_date').data('default-date', $('#m_service_date').val());
            $('#m_service_time').data('default-time', $('#m_service_time').val());
        }
        $('#e_subsidiary_origin').trigger('change');
        $('#e_type_guide').trigger('change');
        if ($('#e_type_bill').length) {
            loadDocumentNumbers('E', $('#e_type_bill').val() || 'T');
        }
        recalcEncomiendaTotals();
        updateServiceDetailState($('#m_inventory_body'), $('#m_inventory_empty'), $('#m_detail_count'));
        updateServiceDetailState($('#d_shipment_body'), $('#d_shipment_empty'), $('#d_detail_count'));
        updateServiceDetailState($('#c_cargo_body'), $('#c_cargo_empty'), $('#c_detail_count'));
        checkCashStatus();
    }

    return { init: init, setService: setService, loadDocumentNumbers: loadDocumentNumbers };
})(jQuery);
