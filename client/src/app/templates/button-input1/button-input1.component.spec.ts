import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ButtonInput1Component } from './button-input1.component';

describe('ButtonInput1Component', () => {
  let component: ButtonInput1Component;
  let fixture: ComponentFixture<ButtonInput1Component>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ButtonInput1Component]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ButtonInput1Component);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
