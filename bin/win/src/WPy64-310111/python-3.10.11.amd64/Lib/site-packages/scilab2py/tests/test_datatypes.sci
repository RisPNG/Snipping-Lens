
function [data] = test_datatypes()
    // Test of returning a structure with multiple
    // nesting and multiple return types
    // Add a UTF char for test: 猫

    //////////////////////////////
    // numeric types
    // integers
    data.num.int.int8 = int8(-2^7);
    data.num.int.int16 = int16(-2^15);
    data.num.int.int32 = int32(-2^31);
    data.num.int.uint8 = uint8(2^8-1);
    data.num.int.uint16 = uint16(2^16-1);
    data.num.int.uint32 = uint32(2^32-1);

    // floats
    data.num.double = double(%pi);
    data.num.complex = complex(3, 1)
    data.num.complex_matrix = complex(1.2, 1.1) * eye(3, 3);

    // misc
    data.num.matrix = [1 2; 3 4];
    data.num.vector = [1 2 3 4];
    data.num.column_vector = [1;2;3;4];
    data.num.matrix3d = ones([2 3 4]) * %pi;

    //////////////////////////////
    // string types
    data.string.basic = 'spam';

    //////////////////////////////
    // cell array types
    data.cell.array = {[0.4194 0.3629 -0.0000;
                        0.0376 0.3306 0.0000;
                        0 0 1.0000],
                       [0.5645 -0.2903 0;
                        0.0699 0.1855 0.0000;
                        0.8500 0.8250 1.0000]};

    //////////////////////////////
    // mixed struct
    data.mixed.array = [[1 2]; [3 4]];
    data.mixed.cell = {'1'};
    data.mixed.scalar = 1.8;

endfunction



