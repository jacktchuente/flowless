import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Select2Input } from './select2-input.component';

describe('Select1Input', () => {
  let component: Select2Input;
  let fixture: ComponentFixture<Select2Input>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Select2Input]
    })
    .compileComponents();

    fixture = TestBed.createComponent(Select2Input);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
