import { ComponentFixture, TestBed } from '@angular/core/testing';

import { FormContainer1Component } from './form-container1.component';

describe('FormContainer1Component', () => {
  let component: FormContainer1Component;
  let fixture: ComponentFixture<FormContainer1Component>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [FormContainer1Component]
    })
    .compileComponents();

    fixture = TestBed.createComponent(FormContainer1Component);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
