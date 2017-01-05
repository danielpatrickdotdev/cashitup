$(document).ready(function() {
    // checks if string consists solely of digits (decimals and signs invalid)
    var isNormalInteger = function(str) {
        return /^\d+$/.test(str);
    }
    var recalculateDenomValue = function(denom_input) {
        var count;
        if (isNormalInteger(denom_input.val())) {
            count = parseInt(denom_input.val(), 10);
        } else {
            count = 0;
        }
        var val_input = $("#" + denom_input.attr("name") + "-denom-value");
        var pval = parseInt(val_input.attr("unit_value"), 10);
        val_input.val((count * pval * 0.01).toFixed(2));
    }
    var recalculateTillTotal = function() {
        var sum = 0.0;
        $(".denom-value").each(function() {
            sum += parseFloat($(this).val()) || 0;
        });
        $("#till-total-value").val(sum.toFixed(2));
    }
    var recalculateTakingsTotal = function() {
        var total = parseFloat($("input#id_cash_takings").val()) || 0.0;
        total += parseFloat($("input#id_card_takings").val()) || 0.0;
        $("#total-takings-value").val(total.toFixed(2));
    }
    var recalculateToBankValue = function() {
        var total = parseFloat($("#till-total-value").val()) || 0.0;
        total -= parseFloat($(".float-input").val()) || 0.0;
        $("#till-to-bank-value").val(total.toFixed(2));
    }
    var refreshDifferenceValue = function() {
        var diff = parseFloat($("#till-to-bank-value").val()) || 0.0;
        diff -= parseFloat($("#till-expected-value").val()) || 0.0;
        $("#till-difference-value").val(diff.toFixed(2));
    }
    var refreshExpectedValue = function() {
        var cash = parseFloat($("input#id_cash_takings").val()) || 0.0;
        $("#till-expected-value").val(cash.toFixed(2));
    }
    var recalculateAllDenomValues = function() {
        $(".denom-input").each(function() {
            recalculateDenomValue($(this));
        });
    }
    var recalculateAllValues = function() {
        recalculateTakingsTotal();
        recalculateAllDenomValues();
        recalculateTillTotal();
        recalculateToBankValue();
        refreshExpectedValue();
        refreshDifferenceValue();
    }
    var enforcePrecision = function(elem) {
        elem.val(parseFloat(elem.val()).toFixed(2));
    }
    var enforcePrecisionHandler = function() {
        enforcePrecision($(this));
        //$(this).val(parseFloat($(this).val()).toFixed(2));
    }
    // Recalculate takings whenever a cash/card input is changed
    $(".takings-input").change(function() {
        recalculateTakingsTotal();
        enforcePrecision($(this));
    });
    // Recalculate whenever float changes
    $(".float-input").change(function() {
        recalculateToBankValue();
        refreshDifferenceValue();
        enforcePrecision($(this));
    });
    // Recalculate denoms and figures that depend on them when input is changed
    $(".denom-input").change(function() {
        recalculateDenomValue($(this));
        recalculateTillTotal();
        recalculateToBankValue();
        refreshDifferenceValue();
    });
    // Recalculate expected and difference if cash takings changes
    $(".takings-input#id_cash_takings").change(function() {
        refreshExpectedValue();
        refreshDifferenceValue();
    });
    // Calculate all values on load
    recalculateAllValues();
    // Try to enforce precision on all monetary inputs
    enforcePrecision($(".float-input"));
    //$(".takings-input").each(enforcePrecisionHandler);
});
