#!/usr/bin/env python3


import torch

from .broadcasting import _matmul_broadcast_shape


def left_interp(interp_indices, interp_values, rhs):
    """ """
    is_vector = rhs.ndimension() == 1

    if is_vector:
        res = rhs.index_select(0, interp_indices.view(-1)).view(*interp_values.size())
        res = res.mul(interp_values)
        res = res.sum(-1)
        return res

    else:
        num_rows, num_interp = interp_indices.shape[-2:]
        num_data, num_columns = rhs.shape[-2:]
        interp_shape = torch.Size((*interp_indices.shape[:-1], num_data))
        output_shape = _matmul_broadcast_shape(interp_shape, rhs.shape)
        batch_shape = output_shape[:-2]

        interp_indices_expanded = interp_indices.unsqueeze(-1).expand(*batch_shape, num_rows, num_interp, num_columns)
        interp_values_expanded = interp_values.unsqueeze(-1).expand(*batch_shape, num_rows, num_interp, num_columns)
        rhs_expanded = rhs.unsqueeze(-2).expand(*batch_shape, num_data, num_interp, num_columns)
        res = rhs_expanded.gather(-3, interp_indices_expanded).mul(interp_values_expanded)
        return res.sum(-2)


def left_t_interp(interp_indices, interp_values, rhs, output_dim):
    """ """
    from .. import dsmm

    is_vector = rhs.ndimension() == 1
    if is_vector:
        rhs = rhs.unsqueeze(-1)

    # Multiply the rhs by the interp_values
    # This multiplication here will give us the ability to perform backprop
    values = rhs.unsqueeze(-2) * interp_values.unsqueeze(-1)

    # Define a bunch of sizes
    num_data, num_interp = interp_values.shape[-2:]
    num_cols = rhs.size(-1)
    interp_shape = torch.Size((*interp_indices.shape[:-2], output_dim, num_data))
    output_shape = _matmul_broadcast_shape(interp_shape, rhs.shape)
    batch_shape = output_shape[:-2]
    batch_size = batch_shape.numel()

    # Using interp_indices, create a sparse matrix that will sum up the values
    interp_indices = interp_indices.expand(*batch_shape, *interp_indices.shape[-2:]).contiguous()
    batch_indices = torch.arange(0, batch_size, dtype=torch.long, device=values.device).unsqueeze_(1)
    batch_indices = batch_indices.repeat(1, num_data * num_interp)
    column_indices = torch.arange(0, num_data * num_interp, dtype=torch.long, device=values.device).unsqueeze_(1)
    column_indices = column_indices.repeat(batch_size, 1)
    summing_matrix_indices = torch.stack([batch_indices.view(-1), interp_indices.view(-1), column_indices.view(-1)], 0)
    summing_matrix_values = torch.ones(
        batch_size * num_data * num_interp,
        dtype=interp_values.dtype,
        device=interp_values.device,
    )
    size = torch.Size((batch_size, output_dim, num_data * num_interp))
    type_name = summing_matrix_values.type().split(".")[-1]  # e.g. FloatTensor
    if interp_values.is_cuda:
        cls = getattr(torch.cuda.sparse, type_name)
    else:
        cls = getattr(torch.sparse, type_name)
    summing_matrix = cls(summing_matrix_indices, summing_matrix_values, size)

    # Sum up the values appropriately by performing sparse matrix multiplication
    values = values.reshape(batch_size, num_data * num_interp, num_cols)
    res = dsmm(summing_matrix, values)

    res = res.view(*batch_shape, *res.shape[-2:])
    if is_vector:
        res = res.squeeze(-1)
    return res
