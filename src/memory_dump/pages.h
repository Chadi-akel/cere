/*****************************************************************************
 * This file is part of CERE.                                                *
 *                                                                           *
 * Copyright (c) 2013-2015, Universite de Versailles St-Quentin-en-Yvelines  *
 *                                                                           *
 * CERE is free software: you can redistribute it and/or modify it under     *
 * the terms of the GNU Lesser General Public License as published by        *
 * the Free Software Foundation, either version 3 of the License,            *
 * or (at your option) any later version.                                    *
 *                                                                           *
 * CERE is distributed in the hope that it will be useful,                   *
 * but WITHOUT ANY WARRANTY; without even the implied warranty of            *
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the             *
 * GNU General Public License for more details.                              *
 *                                                                           *
 * You should have received a copy of the GNU General Public License         *
 * along with CERE.  If not, see <http://www.gnu.org/licenses/>.             *
 *****************************************************************************/
#define PAGESIZE 4096
#define CACHELINESIZE 16
#define round_to_page(addr)                                                    \
  ((char *)(((long unsigned)(addr)) & ~(PAGESIZE - 1)))
#define round_up_page(addr) ((((long unsigned)(addr) - 1) / PAGESIZE + 1) * PAGESIZE)
#define nb_pages_in_range(from, to) (((long unsigned)round_up_page(to) - (long unsigned)round_to_page(from))/PAGESIZE)
