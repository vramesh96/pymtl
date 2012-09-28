#=========================================================================
# queues
#=========================================================================
# This file contains a collection of various queue model implementations

from pymtl import *
import pmlib

#-------------------------------------------------------------------------------
# Single-Element Normal Queue Datapath
#-------------------------------------------------------------------------------

class SingleElementNormalQueueDpath (Model):

  def __init__( self, nbits ):

    # Interface Ports

    self.enq_bits  = InPort ( nbits )
    self.deq_bits  = OutPort( nbits )

    # Control signal (ctrl -> dpath)

    self.wen       = InPort ( 1     )

    # Queue storage

    self.queue = pmlib.regs.RegEn( nbits )

    # Connect queue storage

    connect( self.queue.en,  self.wen      )
    connect( self.queue.in_, self.enq_bits )
    connect( self.queue.out, self.deq_bits )

#-------------------------------------------------------------------------------
# Single-Element Normal Queue Control
#-------------------------------------------------------------------------------

class SingleElementNormalQueueCtrl (Model):

  def __init__( self, nbits ):

    # Interface Ports

    self.enq_val  = InPort ( 1 )
    self.enq_rdy  = OutPort( 1 )
    self.deq_val  = OutPort( 1 )
    self.deq_rdy  = InPort ( 1 )

    # Control signal (ctrl -> dpath)

    self.wen      = OutPort( 1 )

    # Full bit storage

    self.full = Wire( 1 )

  @combinational
  def comb( self ):

    # wen control signal: set the write enable signal if the storage queue
    # is empty and a valid enqueue request is present

    self.wen.value       = ~self.full.value & self.enq_val.value

    # enq_rdy signal is asserted when the single element queue storage is
    # empty

    self.enq_rdy.value   = ~self.full.value

    # deq_val signal is asserted when the single element queue storage is
    # full

    self.deq_val.value   = self.full.value

  @posedge_clk
  def seq( self ):

    # full bit calculation: the full bit is cleared when a dequeue
    # transaction occurs, the full bit is set when the queue storage is
    # empty and a enqueue transaction occurs

    if self.reset.value:
      self.full.next = 0
    elif   self.deq_rdy.value and self.deq_val.value:
      self.full.next = 0
    elif self.enq_rdy.value and self.enq_val.value:
      self.full.next = 1
    else:
      self.full.next = self.full.value

#-------------------------------------------------------------------------------
# Single-Element Normal Queue
#-------------------------------------------------------------------------------

class SingleElementNormalQueue (Model):

  def __init__( self, nbits ):

    # Interface Ports

    self.enq_bits = InPort( nbits )
    self.enq_val  = InPort( 1 )
    self.enq_rdy  = OutPort( 1 )

    self.deq_bits = OutPort( nbits )
    self.deq_val  = OutPort( 1 )
    self.deq_rdy  = InPort( 1 )

    # Ctrl and Dpath unit instantiation

    self.ctrl  = SingleElementNormalQueueCtrl( nbits )
    self.dpath = SingleElementNormalQueueDpath( nbits )

    # Ctrl unit connections

    connect( self.ctrl.enq_val, self.enq_val )
    connect( self.ctrl.enq_rdy, self.enq_rdy )
    connect( self.ctrl.deq_val, self.deq_val )
    connect( self.ctrl.deq_rdy, self.deq_rdy )

    # Dpath unit connections

    connect( self.dpath.enq_bits, self.enq_bits )
    connect( self.dpath.deq_bits, self.deq_bits )

    # Control Signal connections (ctrl -> dpath)

    connect( self.dpath.wen,      self.ctrl.wen )

  #-----------------------------------------------------------------------
  # Line tracing
  #-----------------------------------------------------------------------

  def line_trace( self ):

    in_str = \
      pmlib.valrdy.valrdy_to_str( self.enq_bits.value,
        self.enq_val.value, self.enq_rdy.value )

    out_str = \
      pmlib.valrdy.valrdy_to_str( self.deq_bits.value,
        self.deq_val.value, self.deq_rdy.value )

    return "{} () {}"\
      .format( in_str, out_str )

#-------------------------------------------------------------------------------
# Single-Element Bypass Queue Datapath
#-------------------------------------------------------------------------------

class SingleElementBypassQueueDpath (Model):

  def __init__( self, nbits ):

    # Interface Ports

    self.enq_bits  = InPort ( nbits )
    self.deq_bits  = OutPort( nbits )

    # Control signal (ctrl -> dpath)

    self.wen            = InPort ( 1     )
    self.bypass_mux_sel = InPort ( 1     )

    # Queue storage

    self.queue = pmlib.regs.RegEn( nbits )

    connect( self.queue.en,  self.wen      )
    connect( self.queue.in_, self.enq_bits )

    # Bypass mux

    self.bypass_mux = pmlib.muxes.Mux2( nbits )

    connect( self.bypass_mux.in_[0], self.queue.out      )
    connect( self.bypass_mux.in_[1], self.enq_bits       )
    connect( self.bypass_mux.sel,    self.bypass_mux_sel )
    connect( self.bypass_mux.out,    self.deq_bits       )

#-------------------------------------------------------------------------------
# Single-Element Bypass Queue Control
#-------------------------------------------------------------------------------

class SingleElementBypassQueueCtrl (Model):

  def __init__( self, nbits ):

    # Interface Ports

    self.enq_val  = InPort ( 1 )
    self.enq_rdy  = OutPort( 1 )
    self.deq_val  = OutPort( 1 )
    self.deq_rdy  = InPort ( 1 )

    # Control signal (ctrl -> dpath)

    self.wen            = OutPort( 1 )
    self.bypass_mux_sel = OutPort( 1 )

    # Full bit storage

    self.full = Wire( 1 )

  @combinational
  def comb( self ):

    # bypass is always enabled when the queue is empty

    self.bypass_mux_sel.value = ~self.full.value

    # wen control signal: set the write enable signal if the storage queue
    # is empty and a valid enqueue request is present

    self.wen.value       = ~self.full.value & self.enq_val.value

    # enq_rdy signal is asserted when the single element queue storage is
    # empty

    self.enq_rdy.value   = ~self.full.value

    # deq_val signal is asserted when the single element queue storage is
    # full or when the queue is empty but we are bypassing

    self.deq_val.value   = self.full.value | ( ~self.full.value &
                           self.enq_val.value )

  @posedge_clk
  def seq( self ):

    # helper signals

    do_deq    = self.deq_rdy.value and self.deq_val.value
    do_enq    = self.enq_rdy.value and self.enq_val.value
    do_bypass = ~self.full.value and do_deq and do_enq

    # full bit calculation: the full bit is cleared when a dequeue
    # transaction occurs; the full bit is set when the queue storage is
    # empty and a enqueue transaction occurs and when we are not bypassing

    if self.reset.value:
      self.full.next = 0
    elif   do_deq:
      self.full.next = 0
    elif   do_enq and not do_bypass:
      self.full.next = 1
    else:
      self.full.next = self.full.value

#-------------------------------------------------------------------------------
# Single-Element Bypass Queue
#-------------------------------------------------------------------------------

class SingleElementBypassQueue (Model):

  def __init__( self, nbits ):

    # Interface Ports

    self.enq_bits = InPort( nbits )
    self.enq_val  = InPort( 1 )
    self.enq_rdy  = OutPort( 1 )

    self.deq_bits = OutPort( nbits )
    self.deq_val  = OutPort( 1 )
    self.deq_rdy  = InPort( 1 )

    # Ctrl and Dpath unit instantiation

    self.ctrl  = SingleElementBypassQueueCtrl( nbits )
    self.dpath = SingleElementBypassQueueDpath( nbits )

    # Ctrl unit connections

    connect( self.ctrl.enq_val, self.enq_val )
    connect( self.ctrl.enq_rdy, self.enq_rdy )
    connect( self.ctrl.deq_val, self.deq_val )
    connect( self.ctrl.deq_rdy, self.deq_rdy )

    # Dpath unit connections

    connect( self.dpath.enq_bits, self.enq_bits )
    connect( self.dpath.deq_bits, self.deq_bits )

    # Control Signal connections (ctrl -> dpath)

    connect( self.dpath.wen,            self.ctrl.wen            )
    connect( self.dpath.bypass_mux_sel, self.ctrl.bypass_mux_sel )

  #-----------------------------------------------------------------------
  # Line tracing
  #-----------------------------------------------------------------------

  def line_trace( self ):

    in_str = \
      pmlib.valrdy.valrdy_to_str( self.enq_bits.value,
        self.enq_val.value, self.enq_rdy.value )

    out_str = \
      pmlib.valrdy.valrdy_to_str( self.deq_bits.value,
        self.deq_val.value, self.deq_rdy.value )

    return "{} () {}"\
      .format( in_str, out_str )