
function [x, dtype] = roundtrip(y)

  // returns the variable it was given, and optionally the datatype

  x = y;

  if argn(1) == 2

	 dtype = typeof(x);

  end

endfunction
