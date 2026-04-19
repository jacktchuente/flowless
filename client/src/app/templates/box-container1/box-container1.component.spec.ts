import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BoxContainer1Component } from './box-container1.component';

describe('BoxContainer1Component', () => {
  let component: BoxContainer1Component;
  let fixture: ComponentFixture<BoxContainer1Component>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BoxContainer1Component]
    })
    .compileComponents();

    fixture = TestBed.createComponent(BoxContainer1Component);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
