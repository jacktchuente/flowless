import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BoxContainer2Component } from './box-container2.component';

describe('BoxContainer2Component', () => {
  let component: BoxContainer2Component;
  let fixture: ComponentFixture<BoxContainer2Component>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BoxContainer2Component]
    })
    .compileComponents();

    fixture = TestBed.createComponent(BoxContainer2Component);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
