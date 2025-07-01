//----------------------------------------------------------------------------
//  Set absolute path for images
//
//  Copyright (c) 2013- The Spyder Development Team
//
//  Distributed under the terms of the MIT License
//----------------------------------------------------------------------------

//============================================================================
// On document ready
//============================================================================

$(document).ready(function () {
    $('img').attr('src', function(index, attr){
        var path = attr.split('/')
        var img_name = path.reverse()[0]
        return '{{img_path}}' + '/' + img_name
    });
});
