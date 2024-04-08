def test_step(BreakinCycles_fixture):
    step = BreakinCycles_fixture.cycle(0).step(1)
    assert (step.RawData['Step']==5).all()
    
def test_charge(BreakinCycles_fixture):
    charge = BreakinCycles_fixture.cycle(0).charge(0)
    assert (charge.RawData['Step']==6).all()
    assert (charge.RawData['Current (A)']>0).all() 
    
def test_discharge(BreakinCycles_fixture):
    discharge = BreakinCycles_fixture.cycle(0).discharge(0)
    assert (discharge.RawData['Step']==4).all()
    assert (discharge.RawData['Current (A)']<0).all()
    
def test_chargeordischarge(BreakinCycles_fixture):
    charge = BreakinCycles_fixture.cycle(0).chargeordischarge(0)
    assert (charge.RawData['Step']==4).all()
    assert (charge.RawData['Current (A)']<0).all()
    
    discharge = BreakinCycles_fixture.cycle(0).chargeordischarge(1)
    assert (discharge.RawData['Step']==6).all()
    assert (discharge.RawData['Current (A)']>0).all()
    
def test_rest(BreakinCycles_fixture):
    rest = BreakinCycles_fixture.cycle(0).rest(0)
    assert (rest.RawData['Step']==5).all()
    assert (rest.RawData['Current (A)']==0).all()
    
    rest = BreakinCycles_fixture.cycle(0).rest(1)
    assert (rest.RawData['Step']==7).all()
    assert (rest.RawData['Current (A)']==0).all()
    